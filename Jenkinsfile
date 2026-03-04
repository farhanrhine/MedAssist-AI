pipeline {
    agent any

    environment {
        // ── GCP Config ──
        GCP_PROJECT_ID = 'multi-ai-agent-489113'           // TODO: Replace with your GCP project ID
        GCP_REGION = 'us-central1'
        GAR_REPO = 'medassist-ai-repo'                          // Artifact Registry repository name
        CLOUD_RUN_SERVICE = 'medassist-ai-service'
        IMAGE_NAME = 'medassist-ai'
        IMAGE_TAG = 'latest'
    }

    stages {

        stage('Clone GitHub Repo') {
            steps {
                script {
                    echo 'Cloning GitHub repo to Jenkins...'
                    checkout scmGit(
                        branches: [[name: '*/main']],
                        extensions: [],
                        userRemoteConfigs: [[
                            credentialsId: 'github-token',
                            url: 'https://github.com/farhanrhine/MedAssist-AI.git' 
                        ]] // TODO: Replace with  jenkins generate pipeline script stage 1
                    )
                }  
            }
        }

        stage('Build and Scan Docker Image') {
            steps {
                script {
                    echo 'Building Docker image...'
                    sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."

                    echo 'Scanning with Trivy...'
                    sh "trivy image --severity HIGH,CRITICAL --format json -o trivy-report.json ${IMAGE_NAME}:${IMAGE_TAG} || true"

                    archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Push to GCP Artifact Registry') {
            steps {
                withCredentials([file(credentialsId: 'gcp-service-account', variable: 'GCP_KEY')]) {
                    script {
                        def garUrl = "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GAR_REPO}"
                        def imageFullTag = "${garUrl}/${IMAGE_NAME}:${IMAGE_TAG}"

                        sh """
                        gcloud auth activate-service-account --key-file=\$GCP_KEY
                        gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev --quiet
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${imageFullTag}
                        docker push ${imageFullTag}
                        """
                    }
                } // TODO:  change `credentialsId` from jenkins global credentials (stage 2)
            }
        }

        stage('Deploy to GCP Cloud Run') {
            steps {
                withCredentials([file(credentialsId: 'gcp-service-account', variable: 'GCP_KEY')]) {
                    script {
                        def garUrl = "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GAR_REPO}"
                        def imageFullTag = "${garUrl}/${IMAGE_NAME}:${IMAGE_TAG}"

                        echo 'Deploying to GCP Cloud Run...'

                        sh """
                        gcloud auth activate-service-account --key-file=\$GCP_KEY
                        gcloud config set project ${GCP_PROJECT_ID}

                        gcloud run deploy ${CLOUD_RUN_SERVICE} \
                            --image ${imageFullTag} \
                            --region ${GCP_REGION} \
                            --port 5000 \
                            --allow-unauthenticated \
                            --platform managed \
                            --quiet \
                            --set-env-vars GROQ_API_KEY=${GROQ_API_KEY},HUGGINGFACEHUB_API_TOKEN=${HUGGINGFACEHUB_API_TOKEN}
                        """
                    } // TODO: change `credentialsId` from jenkins global credentials (stage 3)
                }
            }
        }
    }

    post {
        success {
            echo '🎉 Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed. Check the logs above.'
        }
    }
}