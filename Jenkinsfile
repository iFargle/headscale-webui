def forgejoImage
def ghcrImage
pipeline {
    agent {
        label 'linux-x64'
    }
    environment {
        APP_VERSION = 'v0.2.1'
    }
    options {
        buildDiscarder(logRotator(numToKeepStr: '100', artifactNumToKeepStr: '20'))
        timestamps()
    }
    stages {
        stage ('Environment') {
            steps {
                sh 'printenv'
            }
        }
        stage('Build') {
            options { timeout(time: 30, unit: 'MINUTES') }
            steps {
                script {
                    forgejoImage = docker.build("albert/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                        + " --build-arg \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                        + " --build-arg \"GIT_BRANCH=${env.BRANCH_NAME}\" "
                        + " ."
                    )
                    ghcrImage = docker.build("ifargle/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                        + " --build-arg \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                        + " --build-arg \"GIT_BRANCH=${env.BRANCH_NAME}\" "
                        + " ."
                    )
                }
            }
        }
        stage('Test') {
            options { timeout(time: 3, unit: 'MINUTES') }
            steps {
                script {
                    forgejoImage.inside { 
                        sh 'ls -lah /app'
                        sh '/app/entrypoint.sh'
                        sh 'python --version'
                    }
                    ghcrImage.inside { 
                        sh 'ls -lah /app'
                        sh '/app/entrypoint.sh'
                        sh 'python --version'
                    }
                }
            }
        }
        stage('Push') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        docker.withRegistry('https://git.sysctl.io/', 'gitea-jenkins-pat') {
                            forgejoImage.push("latest")
                            forgejoImage.push(APP_VERSION)
                        }
                        docker.withRegistry('https://ghcr.io/', 'github-ifargle-pat') {
                            ghcrImage.push("latest")
                            ghcrImage.push(APP_VERSION)
                        }
                    } else {
                        docker.withRegistry('https://git.sysctl.io/', 'gitea-jenkins-pat') {
                            forgejoImage.push("${env.BRANCH_NAME}-${env.BUILD_ID}")
                            forgejoImage.push("${env.BRANCH_NAME}")
                            forgejoImage.push("testing")
                        }
                    }
                }
            }
        }
    }
}
