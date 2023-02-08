def dockerImage
//jenkins needs entrypoint of the image to be empty
def runArgs = '--entrypoint \'\''
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
                    dockerImage = docker.build("albert/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\""
                        + " ."
                    )
                }
            }
        }
        stage('Test') {
            options { timeout(time: 3, unit: 'MINUTES') }
            steps {
                dockerImage.inside { 
                    'cat /etc/hostname'
                }
            }
        }
        stage('Push') {
            when { branch 'testing' }
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script {
                    docker.withRegistry('https://git.sysctl.io/', 'gitea-jenkins-pat') {
                        dockerImage.push("${env.BRANCH_NAME}-${env.BUILD_ID}")
                    }
                }
                milestone 30
            }
        }
    }
}