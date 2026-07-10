pipeline {
    agent any

    environment {
        REGISTRY      = '192.168.188.18:5000'
        IMAGE_NAME    = 'proxy-manager'
        CONTAINER     = 'proxy-manager'
        IMAGE_TAG     = "${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}"
        IMAGE_LATEST  = "${REGISTRY}/${IMAGE_NAME}:latest"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log --oneline -1'
            }
        }

        stage('Build Image') {
            steps {
                // 通过 192.168.188.1:7897 代理下载 mihomo 内核（Jenkins 无法直连 GitHub）
                sh "docker build --build-arg HTTP_PROXY=http://192.168.188.1:7897 --build-arg HTTPS_PROXY=http://192.168.188.1:7897 -t ${IMAGE_NAME} -t ${IMAGE_TAG} -t ${IMAGE_LATEST} ."
            }
        }

        stage('Push to Registry') {
            steps {
                sh "docker push ${IMAGE_TAG}"
                sh "docker push ${IMAGE_LATEST}"
            }
        }

        stage('Deploy to Server') {
            steps {
                sshPublisher(publishers: [
                    sshPublisherDesc(
                        configName: 'hongkong',
                        verbose: true,
                        transfers: [
                            sshTransfer(
                                execCommand: "docker pull ${IMAGE_LATEST} && (docker stop ${CONTAINER} 2>/dev/null || true) && (docker rm ${CONTAINER} 2>/dev/null || true) && (docker volume create proxy-manager-data 2>/dev/null || true) && docker run -d --name ${CONTAINER} --restart unless-stopped -p 8000:8000 -p 7890:7890 -v proxy-manager-data:/app/backend/data -e TZ=Asia/Shanghai -e PROXY_MANAGER_HOST=0.0.0.0 -e PROXY_MANAGER_PORT=8000 ${IMAGE_LATEST} || (echo '=== DEPLOY FAILED, DIAGNOSTICS ===' && docker version 2>&1 && docker info 2>&1 | head -40 && docker ps -a 2>&1 && exit 1)"
                            )
                        ]
                    )
                ])
            }
        }
    }

    post {
        success {
            echo '部署成功！访问 http://38.92.9.207:8000'
        }
        failure {
            echo '部署失败，请检查 Jenkins 日志'
        }
        always {
            sh "docker rmi ${IMAGE_TAG} ${IMAGE_LATEST} ${IMAGE_NAME} 2>/dev/null || true"
            cleanWs()
        }
    }
}
