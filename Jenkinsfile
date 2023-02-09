def forgejoImage
def ghcrImage
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
                    forgejoImage = docker.build("albert/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\""
                        + " ."
                    )
                    ghcrImage = docker.build("iFargle/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\""
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
                        sh 'pip3 list'
                    }
                    ghcrImage.inside { 
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
                        docker.withRegistry('https://git.sysctl.io/', 'gitea-jenkins-pat') {
                            forgejoImage.push("latest")
                        }
                        docker.withRegistry('https://ghcr.io/', 'github-ifargle-pat') {
                            ghcrImage.push("latest")
                        }
                    } else {
                        docker.withRegistry('https://git.sysctl.io/', 'gitea-jenkins-pat') {
                            forgejoImage.push("${env.BRANCH_NAME}-${env.BUILD_ID}")
                        }
                    }
                }
            }
        }
    }
}
