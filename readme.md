---

```markdown
# Zero to GitOps: Deploying a FastAPI App with ArgoCD on Kubernetes

This repository documents my journey of building a local GitOps pipeline from scratch. It is designed as a step-by-step guide for beginners to understand how to containerize an application, deploy it to a local Kubernetes cluster, and manage it using ArgoCD.

## 🛠️ Prerequisites
Before starting, ensure you have the following installed on your machine (this guide uses Windows PowerShell):
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Running)
* [Minikube](https://minikube.sigs.k8s.io/docs/start/)
* [kubectl](https://kubernetes.io/docs/tasks/tools/)
* [Git](https://git-scm.com/)
* Accounts on [GitHub](https://github.com/) and [Docker Hub](https://hub.docker.com/)

---

## Phase 1: Build and Containerize the Application
First, we created a simple Python FastAPI application that displays a welcome message and the name of the Kubernetes pod it is running on.

### 1. The Code (`main.py`)
```python
from fastapi import FastAPI
import os
import socket

app = FastAPI()

@app.get("/")
def read_root():
    hostname = socket.gethostname()
    return {
        "message": "Hello from FastAPI!",
        "pod_name": hostname,
        "status": "Unkillable App is Running"
    }
```

### 2. Dependencies (`requirements.txt`)
```text
fastapi==0.104.1
uvicorn==0.24.0.post1
```

### 3. The Dockerfile
```dockerfile
# Use the official Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY main.py .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. Build and Push to Docker Hub
Open PowerShell and run:
```bash
docker login
docker build -t <your-dockerhub-username>/fastapi-app:v1 .
docker push <your-dockerhub-username>/fastapi-app:v1
```

---

## Phase 2: Create the GitOps Repository (This Repo)
ArgoCD requires a "Single Source of Truth." We created this Git repository to hold our Kubernetes manifests.

### 1. `deployment.yaml`
Tells Kubernetes to pull our Docker image and run 2 replicas.
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-deployment
  labels:
    app: fastapi
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      containers:
      - name: fastapi-container
        image: <your-dockerhub-username>/fastapi-app:v1
        ports:
        - containerPort: 8000
```

### 2. `service.yaml`
Creates a stable network connection (Load Balancer) to route traffic to the pods.
```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
spec:
  selector:
    app: fastapi
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
```

*Push these files to your main GitHub branch.*

---

## Phase 3: Start Kubernetes & Install ArgoCD

### 1. Start the Local Cluster
```bash
minikube start
```
![Insert Kubectl running in terminal Screenshot Here](/screenshot/terminal.JPG)

### 2. Install ArgoCD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f [https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml](https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml)

OR

**Use server-side apply below (this fixes annotation size issues):**
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

```
Verify Pods and wait until all are Running
kubectl get pods -n argocd
```

### 3. Retrieve the ArgoCD Admin Password (Windows PowerShell)
```powershell
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}")))

OR

kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d
```

### 4. Access the Dashboard
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
*Open `https://localhost:8080` in your browser. Log in with username `admin` and the password from the previous step.*

![Insert ArgoCD Login Screenshot Here](/screenshot/Argocd%20login%20page.JPG)

---

## Phase 4: Deploy the App via ArgoCD

In the ArgoCD UI, click **+ New App** and configure:
* **Application Name:** `fastapi-gitops`
* **Project Name:** `default`
* **SYNC POLICY:** `Automatic` (Check "Prune Resources" and "Self Heal")
* **Repository URL:** `https://github.com/<your-username>/argocd-fastapi-config.git`
* **Path:** `./`
* **Cluster URL:** `https://kubernetes.default.svc`
* **Namespace:** `default` *(Warning: Ensure there are no trailing spaces!)*

Click **Create**. ArgoCD will instantly sync your Git repo with your cluster.

![Insert ArgoCD Dashboard Screenshot Here](/screenshot/Argocd%20dashboard.JPG)

---

## Phase 5: Access the App & Test GitOps

### Access the Webpage
Open a new PowerShell terminal and forward the traffic to your local machine:
```bash
kubectl port-forward svc/fastapi-service 8000:80
```
Visit `http://localhost:8000` in your browser!

### Testing the Magic of GitOps
1. **Self-Healing:** Run `kubectl delete pod <pod-name>`. Watch ArgoCD instantly detect the missing pod and spin up a replacement to maintain the desired state.

![Insert ArgoCD Self Healing Screenshot Here](/screenshot/Argocd%20working.JPG)

2. **Git as the Source of Truth:** Edit `deployment.yaml` in GitHub to change `replicas: 2` to `replicas: 4`. Commit the change. Watch ArgoCD automatically spin up two additional pods without touching the terminal!

![Insert ArgoCD Replica Increase Screenshot Here](/screenshot/4%20replicas.JPG)

---

## 🛑 Common Troubleshooting (Lessons Learned)

**Error:** `transport: Error while dialing: dial tcp 10.111.16.119:8081: connect: connection refused`
* **Cause:** The `argocd-repo-server` pod crashed or failed to wake up after a machine sleep.
* **Fix:** Force Kubernetes to restart the pod: `kubectl rollout restart deployment argocd-repo-server -n argocd`

**Error:** `namespaces "default " not found`
* **Cause:** An invisible trailing space was accidentally typed in the Namespace field of the ArgoCD UI.
* **Fix:** Edit the app details in ArgoCD, remove the space so it says exactly `default`, and re-sync.


