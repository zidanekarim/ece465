# Guided Walkthrough: Docker Compose Distributed Image Processor

This directory contains a complete, N-node distributed application designed to perform Histogram Equalization on uploaded image files (JPG/TIFF). It features a real Custom TCP Protocol implementing a Map-Reduce style algorithm to ensure mathematically correct global equalization without visual artifacts. The system is deployed using Docker Compose. (not yet Kubernetes)

## System Architecture

1.  **Frontend (AngularJS)**: A Single Page Application served by the Master node. It features Material Design themed in Cooper Union Maroon (`#990000`).
2.  **Master Node (Python)**:
    *   Runs a FastAPI web server on `8000` to serve the UI and handle file uploads.
    *   Runs a custom AsyncIO TCP server on `6000` to orchestrate Worker nodes.
3.  **Worker Nodes (Python)**:
    *   Connect to the Master node via TCP over port `6000`.
    *   Wait for binary image chunks, process histograms, and map pixel values based on the Master's mathematically derived CDF lookup table.

## The Map-Reduce Custom Protocol

The Master and Workers communicate over a newline-delimited custom TCP protocol transmitting binary byte chunks:
1.  **Register**: Worker sends `REGISTER <id>`. Master acknowledges.
2.  **Map**: Master sends `CALC_HIST` + binary chunks. Workers calculate local 256-bin histograms and return JSON.
3.  **Reduce**: Master aggregates local histograms and computes the Global CDF (Cumulative Distribution Function) Look-up table.
4.  **Apply**: Master sends `APPLY_CDF` + the 256-byte CDF + binary chunks. Workers apply the CDF natively to the byte arrays and return the result.
5.  **Stitch**: Master stitches the chunks back together and saves `<filename>_equalized.<ext>`.

---

## 1. Running Locally (Docker Compose)

Before deploying to a full Kubernetes cluster, you can verify the entire 3-node system locally:

```bash
# Build the Docker images
docker compose build

# Boot the Master and 2 Worker nodes in the background
docker compose up -d

# Check the logs to verify Workers successfully registered with the Master!
docker compose logs -f
```

**Testing the Application:**
1. Open your browser and navigate to `http://localhost:8000`.
2. Login with any username and password (this is a mock login for demonstration).
3. Upload a `.jpg` or `.tiff` file.
4. Click **Equalize Histogram**.
5. Watch the `docker compose logs` to see the Master Map-Reduce the workload across the two Workers over custom TCP.
6. The UI will automatically refresh when complete so you can download the result!

```bash
# Tear down the local cluster once done testing
docker compose down
```

---

## 2. Deploying to Kubernetes (Helm)

To deploy this application to a real Kubernetes cluster utilizing Helm, you must first build and push the Docker images to a registry your K8s cluster can access (e.g., Docker Hub).

### Step 1: Push Images
Assuming your Docker Hub username is `johndoe`:

```bash
# Build Master
docker build -t johndoe/ece465-histogram-master:v1 -f master/Dockerfile .
docker push johndoe/ece465-histogram-master:v1

# Build Worker
docker build -t johndoe/ece465-histogram-worker:v1 -f worker/Dockerfile .
docker push johndoe/ece465-histogram-worker:v1
```

### Step 2: Configure Helm Values
Edit `helm-histogram-eq/values.yaml` to point to your new images:

```yaml
master:
  image:
    repository: johndoe/ece465-histogram-master
    tag: "v1"

worker:
  replicaCount: 5 # Scale up to 5 workers instantly!
  image:
    repository: johndoe/ece465-histogram-worker
    tag: "v1"
```

### Step 3: Deploy!

```bash
# Deploy the packaged Helm chart into K8s
helm install distributed-processor ./helm-histogram-eq
```

*   The Master API will be exposed by the cluster via a `NodePort` or `LoadBalancer` depending on your K8s setup.
*   The Workers will automatically discover the Master's internal cluster IP via the generated DNS name (`distributed-processor-helm-histogram-eq-master-svc`).
*   All images will be saved via a shared `PersistentVolumeClaim`.
