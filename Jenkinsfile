def privateImage // My personal git / container registry
def publicImage  // GitHub Container Registry and Docker Hub
pipeline {
    agent {
        label 'linux-x64'
    }
    environment {
        APP_VERSION    = 'v0.5.4'
        HS_VERSION     = "v0.20.0" // Version of Headscale this is compatible with
        BUILD_DATE     = ''
        BUILDER_NAME   = "multiarch"

        DOCKERHUB_URL  = "https://registry-1.docker.io/"
        DOCKERHUB_CRED = credentials('dockerhub-ifargle-pat')

        GHCR_URL       = "https://ghcr.io/"
        GHCR_CRED      =https://stackoverflow.com/questions/37463489/how-do-i-assure-that-a-jenkins-pipeline-stage-is-always-executed-even-if-a-prev credentials('github-ifargle-pat')

        SYSCTL_URL     = "https://git.sysctl.io/"
        SYSCTL_CRED    = credentials('gitea-jenkins-pat')
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
        stage('Registry Logins') {
            steps {
                sh 'docker login -u ${DOCKERHUB_CRED_USR} -p ${DOCKERHUB_CRED_PSW} $DOCKERHUB_URL'
                sh 'docker login -u ${GHCR_CRED_USR}      -p ${GHCR_CRED_PSW}      $GHCR_URL'
                sh 'docker login -u ${SYSCTL_CRED_USR}    -p ${SYSCTL_CRED_PSW}    $SYSCTL_URL'
            }
        }
        stage('Create Buildx ENV') {
            steps {
                sh """
                    # Create the builder:
                    docker buildx create --name $BUILDER_NAME
                    docker buildx user $BUILDER_NAME
                    docker buildx inspect --bootstrap

                    docker buildx ls
                """
            }
        }
        stage('Build Private') {
            options { timeout(time: 30, unit: 'MINUTES') }
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        privateImage = docker.build("albert/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                            "--label \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                            + " --build-arg GIT_COMMIT_ARG=${env.GIT_COMMIT} "
                            + " --build-arg GIT_BRANCH_ARG=${env.BRANCH_NAME} "
                            + " --build-arg APP_VERSION_ARG=${APP_VERSION} "
                            + " --build-arg BUILD_DATE_ARG=${BUILD_DATE} "
                            + " --build-arg HS_VERSION_ARG=${HS_VERSION} "
                            + " ."
                            + " --platform linux/amd64,linux/arm64,linux/arm/v7,linux/arm/v6"
                            + " -t ${SYSCTL_URL}/albert/headscale-webui:latest"
                            + " -t ${SYSCTL_URL}/albert/headscale-webui:${APP_VERSION}"
                        )
                    } else {
                        privateImage = docker.build("albert/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                            "--label \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                            + " --build-arg GIT_COMMIT_ARG=${env.GIT_COMMIT} "
                            + " --build-arg GIT_BRANCH_ARG=${env.BRANCH_NAME} "
                            + " --build-arg APP_VERSION_ARG=${APP_VERSION} "
                            + " --build-arg BUILD_DATE_ARG=${BUILD_DATE} "
                            + " --build-arg HS_VERSION_ARG=${HS_VERSION} "
                            + " ."
                            + " --platform linux/amd64,linux/arm64,linux/arm/v7,linux/arm/v6"
                            + " -t ${SYSCTL_URL}/albert/headscale-webui:testing"
                            + " -t ${SYSCTL_URL}/albert/headscale-webui:${env.BRANCH_NAME}"
                        )
                    }
                }
            }
        }
        stage('Build Public') {
            options { timeout(time: 30, unit: 'MINUTES') }
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        publicImage = docker.build("ifargle/headscale-webui:${env.BRANCH_NAME}-${env.BUILD_ID}",
                            "--label \"GIT_COMMIT=${env.GIT_COMMIT}\" "
                            + " --build-arg GIT_COMMIT_ARG=${env.GIT_COMMIT} "
                            + " --build-arg GIT_BRANCH_ARG=${env.BRANCH_NAME} "
                            + " --build-arg APP_VERSION_ARG=${APP_VERSION} "
                            + " --build-arg BUILD_DATE_ARG=${BUILD_DATE} "
                            + " --build-arg HS_VERSION_ARG=${HS_VERSION} "
                            + " ."
                            + " --platform linux/amd64,linux/arm64,linux/arm/v7,linux/arm/v6"
                            + " -t ${GHCR_URL}/ifargle/headscale-webui:latest"
                            + " -t ${GHCR_URL}/ifargle/headscale-webui:${APP_VERSION}"
                            + " -t ${DOCKERHUB_URL}/ifargle/headscale-webui:latest"
                            + " -t ${DOCKERHUB_URL}/ifargle/headscale-webui:${APP_VERSION}"
                        )
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                sh """
                    docker buildx use default
                    docker buildx rm $BUILDER_NAME

                    ## Sanity check step
                    docker buildx ls
                    docker logout

                    docker system prune --force
                """
            }
        }
    }
}
