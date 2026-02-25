# MEDICAL RAG CHATBOT

## Clone the Project

```bash
git clone https://github.com/data-guru0/LLMOPS-2-TESTING-MEDICAL.git
cd LLMOPS-2-TESTING-MEDICAL
```

## Create a Virtual Environment (Windows)

```bash
python -m venv venv
venv\Scripts\activate
```

## Install Dependencies

```bash
pip install -e .
```

## ✅ Prerequisites Checklist (Complete These Before Moving Forward)

- [ ] **Docker Desktop** is installed and running in the background
- [ ] **Code versioning** is properly set up using GitHub (repository pushed and updated)
- [ ] **Dockerfile** is created and configured for the project
- [ ] **Dockerfile** is also created and configured for **Jenkins**

## ==> 1. 🚀 Jenkins Setup for Deployment

### 1. Create Jenkins Setup Directory and Dockerfile

- Create a folder named `custom_jenkins`
- Inside `custom_jenkins`, create a `Dockerfile` and add the necessary Jenkins + Docker-in-Docker configuration code

### 2. Build Jenkins Docker Image

Open terminal and navigate to the folder:

```bash
cd custom_jenkins
```

Make sure **Docker Desktop is running in the background**, then build the image:

```bash
docker build -t jenkins-dind .
```

### 3. Run Jenkins Container

```bash
docker run -d ^
  --name jenkins-dind ^
  --privileged ^
  -p 8080:8080 ^
  -p 50000:50000 ^
  -v /var/run/docker.sock:/var/run/docker.sock ^
  -v jenkins_home:/var/jenkins_home ^
  jenkins-dind
```

> ✅ If successful, you'll get a long alphanumeric container ID

### 4. Check Jenkins Logs and Get Initial Password

```bash
docker ps
docker logs jenkins-dind
```

If the password isn't visible, run:

```bash
docker exec jenkins-dind cat /var/jenkins_home/secrets/initialAdminPassword
```

### 5. Access Jenkins Dashboard

- Open your browser and go to: [http://localhost:8080](http://localhost:8080)

### 6. Install Python Inside Jenkins Container

Back in the terminal:

```bash
docker exec -u root -it jenkins-dind bash
apt update -y
apt install -y python3
python3 --version
ln -s /usr/bin/python3 /usr/bin/python
python --version
apt install -y python3-pip
exit
```

### 7. Restart Jenkins Container

```bash
docker restart jenkins-dind
```

### 8. Go to Jenkins Dashboard and Sign In Again

## ==> 2. 🔗 Jenkins Integration with GitHub

### 1. Generate a GitHub Personal Access Token

- Go to **GitHub** → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
- Click **Generate new token (classic)**
- Provide:
  - A **name** (e.g., `Jenkins Integration`)
  - Select scopes:
    - `repo` (for full control of private repositories)
    - `admin:repo_hook` (for webhook integration)

- Generate the token and **save it securely** (you won't see it again!).

> ℹ️ **What is this token?**
> A GitHub token is a secure way to authenticate Jenkins (or any CI/CD tool) to access your GitHub repositories without needing your GitHub password. It's safer and recommended over using plain credentials.

---

### 2. Add GitHub Token to Jenkins Credentials

- Go to **Jenkins Dashboard** → **Manage Jenkins** → **Credentials** → **(Global)** → **Add Credentials**
- Fill in the following:
  - **Username:** Your GitHub username
  - **Password:** Paste the GitHub token you just generated
  - **ID:** `github-token`
  - **Description:** `GitHub Token for Jenkins`

Click **Save**.

---

### 3. Create a New Pipeline Job in Jenkins

- Go back to **Jenkins Dashboard**
- Click **New Item** → Select **Pipeline**
- Enter a name (e.g., `medical-rag-pipeline`)
- Click **OK** → Scroll down, configure minimal settings → Click **Save**

> ⚠️ You will have to configure pipeline details **again** in the next step

---

### 4. Generate Checkout Script from Jenkins UI

- In the left sidebar of your pipeline project, click **Pipeline Syntax**
- From the dropdown, select **`checkout: General SCM`**
- Fill in:
  - SCM: Git
  - Repository URL: Your GitHub repo URL
  - Credentials: Select the `github-token` you just created
- Click **Generate Pipeline Script**
- Copy the generated Groovy script (e.g., `checkout([$class: 'GitSCM', ...])`)

---

### 5. Create a `Jenkinsfile` in Your Repo ( Already done )

- Open your project in **VS Code**
- Create a file named `Jenkinsfile` in the root directory

### 6. Push the Jenkinsfile to GitHub

```bash
git add Jenkinsfile
git commit -m "Add Jenkinsfile for CI pipeline"
git push origin main
```

---

### 7. Trigger the Pipeline

- Go to **Jenkins Dashboard** → Select your pipeline → Click **Build Now**

🎉 **You'll see a SUCCESS message if everything works!**

✅ **Your GitHub repository has been cloned inside Jenkins' workspace!**

---

> 🔁 If you already cloned the repo with a `Jenkinsfile` in it, you can skip creating a new one manually.

## ==> 3. 🐳 Build Docker Image, Scan with Trivy, and Push to Registry

### 1. Install Trivy in Jenkins Container

```bash
docker exec -u root -it jenkins-dind bash
apt install -y
curl -LO https://github.com/aquasecurity/trivy/releases/download/v0.62.1/trivy_0.62.1_Linux-64bit.deb
dpkg -i trivy_0.62.1_Linux-64bit.deb
trivy --version
exit
```

Then restart the container:

```bash
docker restart jenkins-dind
```

---

### 2. Install Cloud Plugins in Jenkins

#### 🅰️ AWS — Install AWS Plugins

- Go to **Jenkins Dashboard** → **Manage Jenkins** → **Plugins**
- Install:
  - **AWS SDK**
  - **AWS Credentials**
- Restart the Jenkins container:

```bash
docker restart jenkins-dind
```

#### ☁️ GCP — Install GCP Plugins

- Go to **Jenkins Dashboard** → **Manage Jenkins** → **Plugins**
- Install:
  - **Google OAuth Credentials**
  - **Google Artifact Registry Auth** (if available, otherwise not required)
- Restart the Jenkins container:

```bash
docker restart jenkins-dind
```

---

### 3. Create Cloud Credentials

#### 🅰️ AWS — Create IAM User

- Go to **AWS Console** → **IAM** → **Users** → **Add User**
- Assign **programmatic access**
- Attach policy: `AmazonEC2ContainerRegistryFullAccess`
- After creation, generate **Access Key + Secret**

#### ☁️ GCP — Create Service Account

- Go to **GCP Console** → **IAM & Admin** → **Service Accounts** → **Create Service Account**
- Name it (e.g., `jenkins-deployer`)
- Assign roles:
  - `Artifact Registry Writer` (to push images)
  - `Cloud Run Admin` (to deploy)
  - `Service Account User` (required for Cloud Run deployments)
- Click **Done** → Click on the created service account → **Keys** tab → **Add Key** → **Create new key** → **JSON**
- Download the JSON key file and **save it securely**

> ℹ️ **What is this JSON key?**
> A GCP service account key is the equivalent of AWS Access Key + Secret. It authenticates Jenkins to interact with GCP services like Artifact Registry and Cloud Run.

---

### 4. Add Cloud Credentials to Jenkins

#### 🅰️ AWS — Add AWS Credentials

- Go to **Jenkins Dashboard** → **Manage Jenkins** → **Credentials**
- Click on **(Global)** → **Add Credentials**
- Select **AWS Credentials**
- Add:
  - **Access Key ID**
  - **Secret Access Key**
- Give an ID (e.g., `aws-ecr-creds`) and Save

#### ☁️ GCP — Add GCP Credentials

- Go to **Jenkins Dashboard** → **Manage Jenkins** → **Credentials**
- Click on **(Global)** → **Add Credentials**
- Select **Secret file**
- Upload the **JSON key file** you downloaded from GCP
- Give an ID (e.g., `gcp-service-account`) and Save

---

### 5. Install Cloud CLI Inside Jenkins Container

#### 🅰️ AWS — Install AWS CLI

```bash
docker exec -u root -it jenkins-dind bash
apt update
apt install -y unzip curl
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
aws --version
exit
```

#### ☁️ GCP — Install Google Cloud CLI (`gcloud`)

```bash
docker exec -u root -it jenkins-dind bash
apt update
apt install -y curl apt-transport-https ca-certificates gnupg
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list
apt update
apt install -y google-cloud-cli
gcloud --version
exit
```

---

### 6. Create a Container Registry Repository

#### 🅰️ AWS — Create ECR Repository

- Go to **AWS Console** → **ECR** → **Create Repository**
- Note the **repository URI** (e.g., `123456789.dkr.ecr.us-east-1.amazonaws.com/medical-rag`)

#### ☁️ GCP — Create Artifact Registry Repository

- Go to **GCP Console** → **Artifact Registry** → **Create Repository**
- Fill in:
  - **Name:** `medical-rag` (or your preferred name)
  - **Format:** Docker
  - **Region:** Choose your region (e.g., `us-central1`)
- Click **Create**
- Note the **repository path** (e.g., `us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-rag`)

> ℹ️ **GCP Artifact Registry** is the GCP equivalent of AWS ECR. It stores your Docker images and integrates directly with Cloud Run for deployment.

---

### 7. Add Build, Scan, and Push Stage in Jenkinsfile ( Already done if cloned )

#### ☁️ GCP — Key Differences in Jenkinsfile

If using GCP instead of AWS, update these parts in your `Jenkinsfile`:

**Authentication (replace AWS ECR login):**

```groovy
// AWS ECR login:
// sh "aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ECR_URI>"

// GCP Artifact Registry login:
sh "gcloud auth activate-service-account --key-file=${GCP_KEY}"
sh "gcloud auth configure-docker us-central1-docker.pkg.dev --quiet"
```

**Push image (replace ECR URI with Artifact Registry URI):**

```groovy
// AWS:
// sh "docker tag medical-rag:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/medical-rag:latest"
// sh "docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/medical-rag:latest"

// GCP:
sh "docker tag medical-rag:latest us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-rag/medical-rag:latest"
sh "docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-rag/medical-rag:latest"
```

> 🔐 **Tip**: Change `--exit-code 0` to `--exit-code 1` in Trivy to make the pipeline fail on vulnerabilities.

---

### 8. Fix Docker Daemon Issues (If Any)

If you encounter Docker socket permission issues, fix with:

```bash
docker exec -u root -it jenkins-dind bash
chown root:docker /var/run/docker.sock
chmod 660 /var/run/docker.sock
getent group docker
# If group 'docker' exists, skip next line
usermod -aG docker jenkins
exit

docker restart jenkins-dind
```

Then open **Jenkins Dashboard** again to continue.

## ==> 4. 🚀 Deployment to Cloud Service

### ✅ Prerequisites

1. **Jenkinsfile Deployment Stage** ( Already done if cloned )

---

### 🅰️ AWS — Deployment to AWS App Runner

#### 🔐 IAM User Permissions

- Go to **AWS Console** → **IAM** → Select your Jenkins user
- Attach the policy: `AWSAppRunnerFullAccess`

#### 🌐 Setup AWS App Runner (Manual Step)

1. Go to **AWS Console** → **App Runner**
2. Click **Create service**
3. Choose:
   - **Source**: Container registry (ECR)
   - Select your image from ECR
4. Configure runtime, CPU/memory, and environment variables
5. Set auto-deploy from ECR if desired
6. Deploy the service

📺 Follow the tutorial video instructions for correct setup

---

### ☁️ GCP — Deployment to Google Cloud Run

#### 🔐 Service Account Permissions

- Go to **GCP Console** → **IAM & Admin** → **IAM**
- Find your `jenkins-deployer` service account
- Ensure it has these roles (should already be set from Step 3):
  - `Cloud Run Admin`
  - `Service Account User`
  - `Artifact Registry Reader`

#### 🌐 Setup Cloud Run (Manual — First Time)

1. Go to **GCP Console** → **Cloud Run**
2. Click **Create Service**
3. Choose:
   - **Source**: Select the container image from **Artifact Registry**
   - Image URL: `us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-rag/medical-rag:latest`
4. Configure:
   - **Service name:** `medical-rag-chatbot`
   - **Region:** Your preferred region (e.g., `us-central1`)
   - **CPU/Memory:** 1 vCPU, 512 MiB (adjust as needed)
   - **Port:** `5000` (matches your Flask app)
   - **Environment variables:** Add your `.env` variables (`GROQ_API_KEY`, `HUGGINGFACEHUB_API_TOKEN`, etc.)
   - **Authentication:** Select **Allow unauthenticated invocations** (for public access)
5. Click **Create** and wait for deployment

> ℹ️ **Cloud Run** is the GCP equivalent of AWS App Runner. It runs your container serverlessly — you only pay when requests are being processed. It auto-scales to zero when idle.

#### 🤖 Deploy via CLI (Automated — From Jenkinsfile)

Add this to your Jenkinsfile's deploy stage for GCP:

```groovy
stage('Deploy to Cloud Run') {
    steps {
        withCredentials([file(credentialsId: 'gcp-service-account', variable: 'GCP_KEY')]) {
            sh """
                gcloud auth activate-service-account --key-file=\$GCP_KEY
                gcloud config set project YOUR_PROJECT_ID
                gcloud run deploy medical-rag-chatbot \
                    --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-rag/medical-rag:latest \
                    --region us-central1 \
                    --port 5000 \
                    --allow-unauthenticated \
                    --set-env-vars "GROQ_API_KEY=your-key,HUGGINGFACEHUB_API_TOKEN=your-token"
            """
        }
    }
}
```

> ⚠️ **Important:** Replace `YOUR_PROJECT_ID` with your actual GCP project ID. For secrets, consider using **GCP Secret Manager** instead of plain env vars in production.

---

### 🧪 Run Jenkins Pipeline

- Go to **Jenkins Dashboard** → Select your pipeline job
- Click **Build Now**

If all stages succeed (Checkout → Build → Trivy Scan → Push to Registry → Deploy):

🎉 **CI/CD Deployment is complete!**

✅ Your app is now live and running on **AWS App Runner** or **GCP Cloud Run** 🚀

---

## 📋 Quick Reference: AWS vs GCP Services

| Purpose | AWS Service | GCP Service |
|---|---|---|
| Container Registry | ECR (Elastic Container Registry) | Artifact Registry |
| Serverless Container Hosting | App Runner | Cloud Run |
| Identity & Access | IAM Users + Access Keys | Service Accounts + JSON Keys |
| CLI Tool | `aws` CLI | `gcloud` CLI |
| Credentials in Jenkins | AWS Credentials plugin | Secret file (JSON key) |
| Auth Command | `aws ecr get-login-password` | `gcloud auth configure-docker` |
