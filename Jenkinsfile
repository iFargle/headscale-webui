def privateImage // My personal git / container registry
def publicImage  // GitHub Container Registry and Docker Hub
pipeline {
    agent {
        label 'linux-x64'
    }
    environment {
        APP_VERSION = 'v0.5.0'
        HS_VERSION  = "v0.20.0" // Version of Headscale this is compatible with
        BUILD_DATE  = ''
    }
    options {
        buildDiscarder(logRotator(numToKeepStr: '100', artifactNumToKeepStr: '20'))
        timestamps()
    }
    stages {
        stage ('ENV') {
            steps {
                sh 'printenv'
                script { BUILD_DATE = java.time.LocalDate.now() }
            }
        }
        stage('Build') {
            options { timeout(time: 30, unit: 'MINUTES') }
            steps {
                script {
                    privateImage = docker.build("albert/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                        + " --build-arg GIT_COMMIT_ARG=${env.GIT_COMMIT} "
                        + " --build-arg GIT_BRANCH_ARG=${env.BRANCH_NAME} "
                        + " --build-arg APP_VERSION_ARG=${APP_VERSION} "
                        + " --build-arg BUILD_DATE_ARG=${BUILD_DATE} "
                        + " --build-arg HS_VERSION_ARG=${HS_VERSION} "
                        + " ."
                    )
                    publicImage = docker.build("ifargle/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                        + " --build-arg GIT_COMMIT_ARG=${env.GIT_COMMIT} "
                        + " --build-arg GIT_BRANCH_ARG=${env.BRANCH_NAME} "
                        + " --build-arg APP_VERSION_ARG=${APP_VERSION} "
                        + " --build-arg BUILD_DATE_ARG=${BUILD_DATE} "
                        + " --build-arg HS_VERSION_ARG=${HS_VERSION} "
                        + " ."
                    )
                }
            }
        }
        stage('Test') {
            options { timeout(time: 3, unit: 'MINUTES') }
            steps {
                script {
                    privateImage.inside { 
                        sh 'ls -lah /app'
                        sh 'python --version'
                        sh 'pip list'
                    }
                    publicImage.inside { 
                        sh 'ls -lah /app'
                        sh 'python --version'
                        sh 'pip list'
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
                            privateImage.push("latest")
                            privateImage.push(APP_VERSION)
                        }
                        docker.withRegistry('https://ghcr.io/', 'github-ifargle-pat') {
                            publicImage.push("latest")
                            publicImage.push(APP_VERSION)
                        }
                        docker.withRegistry('https://registry-1.docker.io/', 'dockerhub-ifargle-pat') {
                            publicImage.push("latest")
                            publicImage.push(APP_VERSION)
                        }
                    } else {
                        docker.withRegistry('https://git.sysctl.io/', 'gitea-jenkins-pat') {
                            privateImage.push("${env.BRANCH_NAME}-${env.BUILD_ID}")
                            privateImage.push("${env.BRANCH_NAME}")
                            privateImage.push("testing")
                        }
                    }
                }
            }
        }
        stage('Clean') {
            options { timeout(time: 3, unit: 'MINUTES') }
            steps {
                script {
                    sh 'docker system prune --force'
                }
            }
        }
    }
}
