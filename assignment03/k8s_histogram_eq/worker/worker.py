import asyncio
import os
import socket
import logging
import numpy as np
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WorkerNode")

MASTER_HOST = os.environ.get("MASTER_HOST", "127.0.0.1")
MASTER_PORT = int(os.environ.get("MASTER_PORT", 6000))
# Let the worker ID be its hostname
WORKER_ID = socket.gethostname()

async def log_to_master(writer, msg):
    logger.info(msg)
    if writer:
        try:
            header = f"LOG {WORKER_ID} {msg}\n"
            writer.write(header.encode('utf-8'))
            await writer.drain()
        except:
            pass

async def worker_loop():
    logger.info(f"Worker {WORKER_ID} starting up. Pointing to Master {MASTER_HOST}:{MASTER_PORT}")
    
    while True:
        try:
            reader, writer = await asyncio.open_connection(MASTER_HOST, MASTER_PORT)
            logger.info("Connected to Master.")
            
            # Phase 0: Register
            register_msg = f"REGISTER {WORKER_ID}\n"
            writer.write(register_msg.encode('utf-8'))
            await writer.drain()
            
            ack = await reader.readline()
            if ack.decode('utf-8').strip() == "ACK_REGISTER":
                logger.info("Successfully registered with Master.")
                await log_to_master(writer, "Successfully registered with Master and awaiting jobs.")
                
            while True:
                line = await reader.readline()
                if not line:
                    logger.warning("Connection closed by Master.")
                    break
                    
                msg = line.decode('utf-8').strip()
                if not msg:
                    continue
                    
                parts = msg.split()
                cmd = parts[0]
                
                if cmd == "CALC_HIST":
                    job_id = parts[1]
                    chunk_size = int(parts[2])
                    
                    logger.info(f"[{job_id}] Received CALC_HIST for {chunk_size} bytes.")
                    await log_to_master(writer, f"[{job_id}] Phase 1: Calculating local histogram mapping...")
                    chunk_bytes = await reader.readexactly(chunk_size)
                    
                    # Convert to numpy array of uint8
                    arr = np.frombuffer(chunk_bytes, dtype=np.uint8)
                    
                    # Calculate 256-bin histogram
                    hist, _ = np.histogram(arr, bins=256, range=(0, 256))
                    hist_list = hist.tolist()
                    
                    # Send response
                    header = f"HIST_RESULT {job_id}\n"
                    writer.write(header.encode('utf-8'))
                    writer.write((json.dumps(hist_list) + "\n").encode('utf-8'))
                    await writer.drain()
                    logger.info(f"[{job_id}] Sent HIST_RESULT.")
                    await log_to_master(writer, f"[{job_id}] Sent HIST_RESULT back to Master.")
                    
                elif cmd == "APPLY_CDF":
                    job_id = parts[1]
                    chunk_size = int(parts[2])
                    
                    logger.info(f"[{job_id}] Received APPLY_CDF for {chunk_size} bytes.")
                    await log_to_master(writer, f"[{job_id}] Phase 3: Applying Global CDF mapping to chunk.")
                    
                    # First read the 256 byte CDF array
                    cdf_bytes = await reader.readexactly(256)
                    cdf = np.frombuffer(cdf_bytes, dtype=np.uint8)
                    
                    # Next read the raw image chunk
                    chunk_bytes = await reader.readexactly(chunk_size)
                    arr = np.frombuffer(chunk_bytes, dtype=np.uint8)
                    
                    # Map pixels using the CDF lookup table
                    # Numpy advanced indexing acts incredibly fast here
                    mapped_arr = cdf[arr]
                    
                    mapped_bytes = mapped_arr.tobytes()
                    header = f"MAPPED_RESULT {job_id} {len(mapped_bytes)}\n"
                    
                    writer.write(header.encode('utf-8'))
                    writer.write(mapped_bytes)
                    await writer.drain()
                    logger.info(f"[{job_id}] Sent MAPPED_RESULT ({len(mapped_bytes)} bytes).")
                    await log_to_master(writer, f"[{job_id}] Sent Processed MAPPED_RESULT back to Master.")

        except Exception as e:
            logger.error(f"Error connecting to master: {e}")
            await asyncio.sleep(5) # Reconnect delay

if __name__ == '__main__':
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker shutting down.")
