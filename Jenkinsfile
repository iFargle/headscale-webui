pipeline {
    agent any
    stages {
        stage('Build - headscale-webui') {
            steps {
                agent {
                    dockerfile {
                        filename 'Dockerfile'
                        additionalBuildArgs "-t git.sysctl.io/albert/headscale-webui:jenkins-${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
                    }
                }
            }
        }
    }
    post {
        always {
            echo 'Finished'
        }
        success {
            echo 'This will run only if successful'
            /* Upload to Registry and tag with latest and build number */
            
            echo 'Tagging successful build as latest'
            sh "docker image tag git.sysctl.io/albert/headscale-webui:jenkins-${env.BRANCH_NAME}-${env.BUILD_NUMBER} git.sysctl.io/albert/headscale-webui:latest"

            echo 'Uploading to Docker Registry:'
            sh 'docker image push registry.sysctl.io/ifargle/feedbin-extract:latest'

            sh 'docker image ls | grep feedbin'
            deleteDir()

        }
        failure {
            echo 'Cleaning up'
            sh 'docker rmi --force $(docker images --quiet --filter=reference="git.sysctl.io/albert/headscale-webui")'
            deleteDir()

            echo 'This will run only if failed'
            mail to:      'albert@sysctl.io',
                 subject: "Failed Pipeline: ${currentBuild.fullDisplayName} - headscale-webui branch:  ${env.BRANCH_NAME}",
                 body:    "Something is wrong with ${env.BUILD_URL}"
        }
    }
}