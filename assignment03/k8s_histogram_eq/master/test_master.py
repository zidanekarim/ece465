import pytest
from fastapi.testclient import TestClient
from main import app, UPLOAD_DIR_STR
import os

client = TestClient(app)

def test_upload_file():
    # Create a dummy file
    file_content = b"fake image bytes"
    response = client.post(
        "/upload",
        files={"file": ("test_image.jpg", file_content, "image/jpeg")}
    )
    assert response.status_code == 200
    assert response.json() == {"filename": "test_image.jpg", "status": "uploaded"}
    
    # Verify file is on disk
    assert os.path.exists(f"{UPLOAD_DIR_STR}/test_image.jpg")
    
    # Clean up
    if os.path.exists(f"{UPLOAD_DIR_STR}/test_image.jpg"):
        os.remove(f"{UPLOAD_DIR_STR}/test_image.jpg")

def test_upload_invalid_extension():
    file_content = b"fake text bytes"
    response = client.post(
        "/upload",
        files={"file": ("test.txt", file_content, "text/plain")}
    )
    assert response.status_code == 400
    assert "detail" in response.json()

def test_listing_and_deletion():
    # 1. Upload a dummy image purely for deletion testing
    file_content = b"fake image bytes"
    client.post(
        "/upload",
        files={"file": ("delete_me.jpg", file_content, "image/jpeg")}
    )
    
    # 2. Assert it's in the list
    response = client.get("/files")
    assert response.status_code == 200
    files = [f["name"] for f in response.json()["files"]]
    assert "delete_me.jpg" in files
    
    # 3. Request deletion
    del_response = client.delete("/files/delete_me.jpg")
    assert del_response.status_code == 200
    
    # 4. Assert it's gone
    assert not os.path.exists(f"{UPLOAD_DIR_STR}/delete_me.jpg")

def test_diagnostic_endpoints():
    r1 = client.get("/nodes")
    assert r1.status_code == 200
    assert "connected_workers" in r1.json()

    r2 = client.get("/logs")
    assert r2.status_code == 200
    assert "logs" in r2.json()
    
    r3 = client.post("/clear_logs")
    assert r3.status_code == 200
    
    r4 = client.get("/logs")
    assert len(r4.json()["logs"]) == 0
