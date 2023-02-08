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
                    dockerImage = docker.build("headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                        "--label \"GIT_COMMIT=${env.GIT_COMMIT}\""
                        + " --build-arg MY_ARG=myArg"
                        + " ."
                    )
                }
            }
        }
        stage('Push to docker repository') {
            when { branch 'testing' }
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                lock("${JOB_NAME}-Push") {
                    script {
                        docker.withRegistry('https://git.sysctl.io/', 'docker_registry') {
                            dockerImage.push("${env.BRANCH_NAME}-${env.BUILD_ID}")
                        }
                    }
                    milestone 30
                }
            }
        }
    }
}