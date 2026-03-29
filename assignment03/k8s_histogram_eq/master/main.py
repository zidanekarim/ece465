import asyncio
import os
import cv2
import numpy as np
import logging
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
from datetime import datetime

from fastapi.staticfiles import StaticFiles

# --- Configuration & Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterNode")

UPLOAD_DIR_STR = os.environ.get("UPLOAD_DIR", "/app/shared_data")
UPLOAD_DIR = Path(UPLOAD_DIR_STR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Histogram Equalizer Master")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR_STR = os.environ.get("FRONTEND_DIR", "/app/frontend")

# Serve the static frontend SPA
app.mount("/static", StaticFiles(directory=FRONTEND_DIR_STR), name="static")

# --- Global State for Distributed Processing ---
# Map worker writer streams to IDs
connected_workers = {}
# Thread-safe incrementing job counter
job_counter = 0

# Distributed Logging
app_logs = []

def add_log(source, msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    app_logs.append({"time": timestamp, "source": source, "message": msg})
    if len(app_logs) > 100:
        app_logs.pop(0)

# --- TCP Server (Custom Protocol) ---
async def handle_worker(reader, writer):
    global connected_workers
    addr = writer.get_extra_info('peername')
    logger.info(f"New connection from {addr}")
    add_log("Master", f"New TCP connection from {addr}")
    
    worker_id = None
    try:
        while True:
            # We use a newline-delimited basic header protocol for simplicity, followed by raw bytes if needed
            line = await reader.readline()
            if not line:
                break
            
            msg = line.decode('utf-8').strip()
            if not msg:
                continue
                
            parts = msg.split()
            cmd = parts[0]

            if cmd == "REGISTER":
                worker_id = parts[1] if len(parts) > 1 else str(addr)
                connected_workers[worker_id] = (reader, writer)
                logger.info(f"Worker {worker_id} registered.")
                add_log("Master", f"Worker {worker_id} registered.")
                writer.write(b"ACK_REGISTER\n")
                await writer.drain()
            
            elif cmd == "LOG":
                wid = parts[1]
                log_msg = " ".join(parts[2:])
                add_log(wid, log_msg)
                
            elif cmd == "HIST_RESULT":
                # Expected format: HIST_RESULT <job_id>
                # followed by exactly 256 * 8 bytes (int64) or similar. For simplicity let's say the next line is JSON
                hist_line = await reader.readline()
                hist_data = json.loads(hist_line.decode('utf-8'))
                # In a real system we route this back to the requesting job.
                # Here we will manage it via queues attached to job_id.
                job_id = parts[1]
                if job_id in job_queues:
                    await job_queues[job_id]['hist_queue'].put((worker_id, hist_data))
                    
            elif cmd == "MAPPED_RESULT":
                # Expected: MAPPED_RESULT <job_id> <chunk_size>
                job_id = parts[1]
                chunk_size = int(parts[2])
                # Read exactly chunk_size bytes
                chunk_bytes = await reader.readexactly(chunk_size)
                if job_id in job_queues:
                    await job_queues[job_id]['map_queue'].put((worker_id, chunk_bytes))
                    
    except asyncio.IncompleteReadError:
        pass
    except Exception as e:
        logger.error(f"Error handling worker {addr}: {e}")
    finally:
        if worker_id and worker_id in connected_workers:
            del connected_workers[worker_id]
        logger.info(f"Worker {worker_id or addr} disconnected.")
        writer.close()

# Temporary queues per job to route responses from workers
job_queues = {}

async def tcp_server_task():
    server = await asyncio.start_server(handle_worker, '0.0.0.0', 6000)
    logger.info(f"TCP Coordinator listening on 0.0.0.0:6000")
    async with server:
        await server.serve_forever()

@app.on_event("startup")
async def startup_event():
    # Start the TCP custom protocol server in the background
    asyncio.create_task(tcp_server_task())

# --- Distributed Histogram Equalization Logic ---
async def distribute_job(filename: str, job_id: str):
    file_path = UPLOAD_DIR / filename
    img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        logger.error(f"Failed to load image for job {job_id}")
        return

    workers = list(connected_workers.keys())
    num_workers = len(workers)
    
    if num_workers == 0:
        logger.warning(f"No workers connected for job {job_id}. Processing locally.")
        img_eq = cv2.equalizeHist(img)
        save_path = str(file_path).replace(file_path.suffix, f"_equalized{file_path.suffix}")
        cv2.imwrite(save_path, img_eq)
        return

    logger.info(f"Starting Job {job_id} across {num_workers} workers.")
    
    # 1. Split Image into chunks horizontally (rows)
    height, width = img.shape
    chunk_height = height // num_workers
    chunks = []
    
    for i in range(num_workers):
        start_y = i * chunk_height
        # Last worker takes whatever is left to handle non-divisible heights
        end_y = height if i == num_workers - 1 else (i + 1) * chunk_height
        chunk = img[start_y:end_y, :]
        chunks.append((workers[i], chunk))

    # Setup queues for this job
    job_queues[job_id] = {
        'hist_queue': asyncio.Queue(),
        'map_queue': asyncio.Queue()
    }

    # 2. Map Phase: Calculate local histograms
    # Send chunks to workers
    for wid, chunk in chunks:
        _, writer = connected_workers[wid]
        chunk_bytes = chunk.tobytes()
        header = f"CALC_HIST {job_id} {len(chunk_bytes)}\n"
        writer.write(header.encode('utf-8'))
        writer.write(chunk_bytes)
        await writer.drain()

    # Wait for all histograms
    global_hist = np.zeros(256, dtype=np.int64)
    for _ in range(num_workers):
        _, hist_data = await job_queues[job_id]['hist_queue'].get()
        local_hist = np.array(hist_data, dtype=np.int64)
        global_hist += local_hist

    # 3. Reduce Phase: Calculate CDF at Master
    # Compute the cumulative distribution function
    cdf = global_hist.cumsum()
    cdf_normalized = cdf * float(global_hist.max()) / cdf.max()
    # Create the mapping lookup table
    nj = (cdf - cdf.min()) * 255
    N = cdf.max() - cdf.min()
    if N == 0:
        cdf_mapped = np.arange(256, dtype=np.uint8) # no contrast
    else:
        cdf_mapped = (nj / N).astype('uint8')

    # 4. Apply Phase: Send CDF and chunk back to workers to apply
    cdf_bytes = cdf_mapped.tobytes()
    for wid, chunk in chunks:
        _, writer = connected_workers[wid]
        chunk_bytes = chunk.tobytes()
        header = f"APPLY_CDF {job_id} {len(chunk_bytes)}\n"
        writer.write(header.encode('utf-8'))
        writer.write(cdf_bytes) # exactly 256 bytes
        writer.write(chunk_bytes)
        await writer.drain()

    # Wait for all processed chunks
    processed_chunks_dict = {}
    for _ in range(num_workers):
        wid, p_chunk_bytes = await job_queues[job_id]['map_queue'].get()
        # Find which chunk index this worker had implicitly (assuming static assignment)
        idx = workers.index(wid)
        original_chunk_shape = chunks[idx][1].shape
        p_chunk = np.frombuffer(p_chunk_bytes, dtype=np.uint8).reshape(original_chunk_shape)
        processed_chunks_dict[idx] = p_chunk

    # 5. Stitch Phase
    ordered_chunks = [processed_chunks_dict[i] for i in range(num_workers)]
    final_img = np.vstack(ordered_chunks)
    
    # Save the result
    save_path = str(file_path).replace(file_path.suffix, f"_equalized{file_path.suffix}")
    cv2.imwrite(save_path, final_img)
    logger.info(f"Job {job_id} complete. Saved to {save_path}")
    
    # Cleanup
    del job_queues[job_id]


# --- REST API (Frontend Communication) ---

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        raise HTTPException(status_code=400, detail="Only JPG and TIFF files are permitted.")
    
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    return {"filename": file.filename, "status": "uploaded"}

@app.get("/files")
async def list_files():
    files = []
    if UPLOAD_DIR.exists():
        for item in UPLOAD_DIR.iterdir():
            if item.is_file():
                files.append({"name": item.name, "size": item.stat().st_size})
    return {"files": [f for f in files if "_equalized" not in f["name"]]}

@app.get("/files/equalized")
async def list_equalized_files():
    files = []
    if UPLOAD_DIR.exists():
        for item in UPLOAD_DIR.iterdir():
            if item.is_file() and "_equalized" in item.name:
                files.append({"name": item.name})
    return {"files": files}

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found or already deleted.")
    
    try:
        os.remove(file_path)
        # Also clean up the equalized version if it exists
        eq_file_path = str(file_path).replace(file_path.suffix, f"_equalized{file_path.suffix}")
        if os.path.exists(eq_file_path):
            os.remove(eq_file_path)
            
        logger.info(f"Deleted file {filename} and localized artifacts.")
        add_log("Master", f"Deleted file {filename}.")
        return {"status": "success", "filename": filename}
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/{filename}")
async def process_file(filename: str, background_tasks: BackgroundTasks):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    global job_counter
    job_counter += 1
    job_id = f"job_{job_counter}"
    
    # Run distribution in background
    background_tasks.add_task(distribute_job, filename, job_id)
    return {"status": "processing_started", "job_id": job_id}

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/nodes")
async def get_nodes():
    return {"connected_workers": list(connected_workers.keys())}

@app.get("/logs")
async def get_logs():
    return {"logs": app_logs}

@app.post("/clear_logs")
async def clear_logs():
    app_logs.clear()
    return {"status": "cleared"}

@app.get("/")
async def root():
    return FileResponse(f"{FRONTEND_DIR_STR}/index.html")

# To run for local dev: uvicorn main:app --host 0.0.0.0 --port 8000

