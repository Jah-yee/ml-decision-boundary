#!/usr/bin/env python3
import subprocess, time, json, sys

# Start server
proc = subprocess.Popen(['python3', 'server.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

try:
    # Health check
    r = subprocess.run(['curl', '-s', 'http://localhost:5000/health'], capture_output=True, text=True, timeout=5)
    print("Health:", r.stdout.strip())

    # Train test
    r = subprocess.run([
        'curl', '-s', '-X', 'POST', 'http://localhost:5000/train',
        '-H', 'Content-Type: application/json',
        '-d', '{"model":"SVM","dataset":"circles","p1":50,"p2":50,"n_samples":300}'
    ], capture_output=True, text=True, timeout=15)

    d = json.loads(r.stdout)
    print(f"acc={d['accuracy']:.4f}, time={d['train_time']:.3f}s")
    print(f"grid={len(d['boundary_grid'])}x{len(d['boundary_grid'][0])}")
    print(f"train_pts={len(d['train_points']['xs'])}")
    print(f"model_info={d['model_info']}")
    print("✅ Real training works!")
finally:
    proc.terminate()
    proc.wait()