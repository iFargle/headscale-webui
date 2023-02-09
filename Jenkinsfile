def dockerImage
//jenkins needs entrypoint of the image to be empty
// def runArgs = '--entrypoint \'\''
pipeline {
    agent {
        label 'linux-x64'
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
                    dockerImage = docker.build("headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\""
                        + " ."
                    )
                    dockerImage.tag("git.sysctl.io/albert/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}")  # Forgejo
                    dockerImage.tag("ghcr.io/iFargle/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}")       # GitHub
                }
            }
        }
        stage('Test') {
            options { timeout(time: 3, unit: 'MINUTES') }
            steps {
                script {
                    docker.image("headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}").inside { 
                        sh 'ls -lah /app'
                        sh '/app/entrypoint.sh'
                        sh 'python --version'
                        sh 'pip3 list'
                    }
                }
            }
        }
        stage('Push') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        docker.withRegistry('https://git.sysctl.io/albert/', 'gitea-jenkins-pat') {
                            dockerImage.push("latest")
                        }
                        docker.withRegistry('https://ghcr.io/iFargle/', 'github-ifargle-pat') {
                            dockerImage.push("latest")
                        }
                    } else {
                        docker.withRegistry('https://git.sysctl.io/albert/', 'gitea-jenkins-pat') {
                            dockerImage.push("${env.BRANCH_NAME}-${env.BUILD_ID}")
                        }
                    }
                }
            }
        }
    }
}
