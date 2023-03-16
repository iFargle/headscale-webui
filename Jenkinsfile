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
        GHCR_CRED      = credentials('github-ifargle-pat')

        SYSCTL_URL     = "https://git.sysctl.io/"
        SYSCTL_CRED    = credentials('gitea-jenkins-pat')
    }
    options {
        buildDiscarder(logRotator(numToKeepStr: '100', artifactNumToKeepStr: '20'))
        timestamps()
    }
    stages {
        stage ('Jenkins ENV') {
            steps {
                sh 'printenv'
                script { BUILD_DATE = java.time.LocalDate.now() }
            }
        }
        stage('Create Build ENV') {
            steps {
                sh """
                    # Create the builder:
                    docker buildx create --name $BUILDER_NAME --driver-opt=image=moby/buildkit
                    docker buildx use $BUILDER_NAME
                    docker buildx inspect --bootstrap

                    docker buildx ls
                """

                sh 'docker login -u ${DOCKERHUB_CRED_USR} -p ${DOCKERHUB_CRED_PSW} $DOCKERHUB_URL'
                sh 'docker login -u ${GHCR_CRED_USR}      -p ${GHCR_CRED_PSW}      $GHCR_URL'
                sh 'docker login -u ${SYSCTL_CRED_USR}    -p ${SYSCTL_CRED_PSW}    $SYSCTL_URL'
            }
        }
        stage('Build') {
            options { timeout(time: 8, unit: 'HOURS') }
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        sh """
                            docker buildx build . \
                                -t git.sysctl.io/albert/headscale-webui:latest \
                                -t git.sysctl.io/albert/headscale-webui:${APP_VERSION} \
                                -t docker.io/ifargle/headscale-webui:latest \
                                -t docker.io/ifargle/headscale-webui:${APP_VERSION} \
                                -t ghcr.io/ifargle/headscale-webui:latest \
                                -t ghcr.io/ifargle/headscale-webui:${APP_VERSION} \
                                --build-arg GIT_COMMIT_ARG=${env.GIT_COMMIT} \
                                --build-arg GIT_BRANCH_ARG=${env.BRANCH_NAME} \
                                --build-arg APP_VERSION_ARG=${APP_VERSION} \
                                --build-arg BUILD_DATE_ARG=${BUILD_DATE} \
                                --build-arg HS_VERSION_ARG=${HS_VERSION} \
                                --label \"GIT_COMMIT=${env.GIT_COMMIT}\" \
                                --platform linux/amd64 \
                                --push
                        """
//                              --platform linux/amd64,linux/arm64,linux/arm/v7,linux/arm/v6 \

                    } else { // IF I'm just testing, I don't need to build for ARM
                        sh """
                            docker buildx build . \
                                -t git.sysctl.io/albert/headscale-webui:testing \
                                -t git.sysctl.io/albert/headscale-webui:${env.BRANCH_NAME} \
                                -t ghcr.io/ifargle/headscale-webui:testing \
                                -t ghcr.io/ifargle/headscale-webui:${env.BRANCH_NAME} \
                                --build-arg GIT_COMMIT_ARG=${env.GIT_COMMIT} \
                                --build-arg GIT_BRANCH_ARG=${env.BRANCH_NAME} \
                                --build-arg APP_VERSION_ARG=${APP_VERSION} \
                                --build-arg BUILD_DATE_ARG=${BUILD_DATE} \
                                --build-arg HS_VERSION_ARG=${HS_VERSION} \
                                --label \"GIT_COMMIT=${env.GIT_COMMIT}\" \
                                --platform linux/amd64 \
                                --push
                        """
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
