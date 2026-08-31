import os
import sys
import time
import subprocess
import httpx
from datetime import datetime

# Configure environment for testing
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["USE_BACKGROUND_JOBS"] = "false"
os.environ["USE_MOCK_SIMULATION"] = "true"
os.environ["USE_MOCK_OPTIMIZATION"] = "true"

def run_tests():
    print("=== Starting Uvicorn for testing ===")
    
    # Initialize DB (creates tables in SQLite)
    print("Initializing SQLite DB...")
    # Clean up old test db if exists
    if os.path.exists("./test.db"):
        os.remove("./test.db")
        
    subprocess.run([sys.executable, "-c", "import app.main; from app.database.base import Base; from app.database.session import engine, SessionLocal; from app.database.init_db import init_db; Base.metadata.create_all(bind=engine); init_db(SessionLocal())"], check=True)
    
    # Start server
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(3) # Wait for server to start
    
    try:
        client = httpx.Client(base_url="http://127.0.0.1:8000")
        
        # 1. Health check
        print("\n1. Testing /health")
        r = client.get("/health")
        r.raise_for_status()
        print("   ✅ Health check passed:", r.json())
        
        # 2. Create project
        print("\n2. Testing POST /api/projects")
        r = client.post("/api/projects", json={
            "name": "Test Project v2",
            "description": "Integration test project"
        })
        r.raise_for_status()
        project_id = r.json()["id"]
        print(f"   ✅ Project created (ID: {project_id})")
        
        # 3. Add Climate
        print("\n3. Testing POST /api/projects/{id}/climate")
        r = client.post(f"/api/projects/{project_id}/climate", json={
            "location": "Test City",
            "ambient_temp_c": 25.0,
            "solar_wm2": 800.0,
            "wind_ms": 2.5,
            "humidity_pct": 50.0,
            "mode": "custom"
        })
        r.raise_for_status()
        print("   ✅ Climate added")
        
        # 4. Add Shelter
        print("\n4. Testing POST /api/projects/{id}/shelter")
        r = client.post(f"/api/projects/{project_id}/shelter", json={
            "length": 5.0,
            "width": 4.0,
            "height": 3.0,
            "wall_thickness": 0.2,
            "roof_thickness": 0.15,
            "floor_thickness": 0.15,
            "orientation_deg": 180.0,
            "window_area_m2": 2.0,
            "wall_material_id": 2, # Brick
            "roof_material_id": 1, # Concrete
            "floor_material_id": 1
        })
        r.raise_for_status()
        print("   ✅ Shelter added")
        
        # 5. Validation Check
        print("\n5. Testing GET /api/projects/{id}/validate")
        r = client.get(f"/api/projects/{project_id}/validate")
        r.raise_for_status()
        print("   ✅ Validation result:", r.json())
        
        # 6. Run Simulation
        print("\n6. Testing POST /api/projects/{id}/simulate")
        r = client.post(f"/api/projects/{project_id}/simulate")
        r.raise_for_status()
        sim_data = r.json()
        sim_run_id = sim_data["run_id"]
        print(f"   ✅ Simulation accepted (Run ID: {sim_run_id}), mode: {sim_data['execution_mode']}")
        
        # 7. Check Simulation Status
        print("\n7. Testing GET /api/simulations/{id}/status")
        r = client.get(f"/api/simulations/{sim_run_id}/status")
        r.raise_for_status()
        print("   ✅ Simulation status:", r.json()["status"])
        
        # 8. Get Simulation Result
        print("\n8. Testing GET /api/simulations/{id}/result")
        r = client.get(f"/api/simulations/{sim_run_id}/result")
        r.raise_for_status()
        res_data = r.json()
        print(f"   ✅ Simulation result fetched. Energy kWh: {res_data['total_energy_kwh']}")
        
        # 9. Run Optimization
        print("\n9. Testing POST /api/projects/{id}/optimize")
        r = client.post(f"/api/projects/{project_id}/optimize", json={"objective": "balanced"})
        r.raise_for_status()
        opt_data = r.json()
        opt_run_id = opt_data["run_id"]
        print(f"   ✅ Optimization accepted (Run ID: {opt_run_id})")
        
        # 10. Get Optimization Result
        print("\n10. Testing GET /api/optimization/{id}/result")
        r = client.get(f"/api/optimization/{opt_run_id}/result")
        r.raise_for_status()
        opt_res = r.json()
        print(f"   ✅ Optimization result fetched. Candidates: {len(opt_res['candidates'])}")
        
        # 11. Get Comparison
        print("\n11. Testing GET /api/projects/{id}/comparison")
        r = client.get(f"/api/projects/{project_id}/comparison")
        r.raise_for_status()
        comp_data = r.json()
        print(f"   ✅ Comparison fetched. Energy savings %: {comp_data.get('energy_saving_pct')}")
        
        # 12. Get Recommendation
        print("\n12. Testing GET /api/projects/{id}/recommendation")
        r = client.get(f"/api/projects/{project_id}/recommendation")
        r.raise_for_status()
        print(f"   ✅ Recommendation fetched: {r.json()['summary']}")
        
        # 13. Get Report
        print("\n13. Testing GET /api/projects/{id}/report")
        r = client.get(f"/api/projects/{project_id}/report")
        r.raise_for_status()
        print("   ✅ Report fetched successfully.")

        print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")

    except httpx.HTTPStatusError as e:
        print(f"\n❌ API Test Failed: {e.response.status_code} {e.response.url}")
        print("Response body:", e.response.text)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test Execution Failed: {e}")
        sys.exit(1)
    finally:
        print("\nCleaning up...")
        server.terminate()
        server.wait()

if __name__ == "__main__":
    run_tests()
