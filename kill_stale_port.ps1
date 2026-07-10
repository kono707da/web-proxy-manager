# Kill stale proxy-manager processes on port 8000.
# Only kills processes whose command line looks like our uvicorn / run.py.
# Returns: 0 if port is free (or was freed), 1 if still occupied by us, 2 if occupied by other.

$ErrorActionPreference = 'SilentlyContinue'
$port = 8000

$conns = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
if (-not $conns) {
    Write-Output 'FREE'
    exit 0
}

# 收集占用端口的进程（去重）
$pidSet = @{}
foreach ($c in $conns) {
    $p = $c.OwningProcess
    if ($p -and $p -gt 0) {
        $pidSet[$p] = $true
    }
}
$pids = $pidSet.Keys | Sort-Object

if ($pids.Count -eq 0) {
    Write-Output 'FREE'
    exit 0
}

$owners = @()
foreach ($pid_ in $pids) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pid_" -ErrorAction SilentlyContinue
    $cmd = "$($proc.CommandLine)"
    $name = "$($proc.Name)"
    # 匹配本项目进程：uvicorn 启动 app / run.py 作为参数
    $isOurs = $false
    if ($cmd) {
        if ($cmd -match 'proxy_manager\.main:app') { $isOurs = $true }
        elseif ($cmd -match '\\run\.py') { $isOurs = $true }
        elseif ($cmd -match '/run\.py') { $isOurs = $true }
        elseif ($cmd -match '\srun\.py') { $isOurs = $true }
        elseif ($cmd -match 'uvicorn.*--port\s*8000') { $isOurs = $true }
    }
    $owners += [PSCustomObject]@{
        Pid     = $pid_
        Name    = $name
        CmdLine = $cmd
        IsOurs  = $isOurs
    }
}

Write-Output "FOUND $($owners.Count) process(es) on port ${port}:"
foreach ($o in $owners) {
    $tag = if ($o.IsOurs) { 'OURS' } else { 'OTHER' }
    Write-Output "  [$tag] PID=$($o.Pid) NAME=$($o.Name)"
    Write-Output "        CMD=$($o.CmdLine)"
}

# 杀掉本项目进程
$killed = 0
foreach ($o in $owners) {
    if ($o.IsOurs) {
        Write-Output "Killing PID=$($o.Pid) ($($o.Name))..."
        & taskkill /F /T /PID $o.Pid 2>$null | Out-Null
        Stop-Process -Id $o.Pid -Force -ErrorAction SilentlyContinue
        $killed++
    }
}

if ($killed -gt 0) {
    Write-Output "KILLED $killed of our process(es)."
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 1000
        $recheck = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
        if (-not $recheck) {
            Write-Output "Port $port released after $($i+1)s."
            Write-Output 'FREE'
            exit 0
        }
    }
    Write-Output "ERROR: our process still on port $port after 30s."
    exit 1
} else {
    Write-Output "No our processes to kill. Port held by other program(s)."
    Write-Output 'OTHER'
    exit 2
}
