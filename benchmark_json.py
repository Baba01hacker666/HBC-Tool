import time
import json
import os
import random

try:
    import ujson
except ImportError:
    ujson = None

try:
    import orjson
except ImportError:
    orjson = None

print("Generating 1,000,000 dummy objects to simulate a large Hermes bundle...")
data = []
for i in range(1000000):
    data.append({
        "id": i,
        "name": f"string_value_{i}",
        "active": i % 2 == 0,
        "attributes": [random.random(), random.randint(0, 1000)]
    })

def test_lib(lib_name, dumps_func, loads_func, is_bytes=False):
    print(f"\n--- Testing {lib_name} ---")
    
    start = time.time()
    serialized = dumps_func(data)
    dump_time = time.time() - start
    
    with open("test_bench.json", "wb" if is_bytes else "w") as f:
        f.write(serialized)
        
    size = os.path.getsize("test_bench.json") / (1024 * 1024)
    
    with open("test_bench.json", "rb" if is_bytes else "r") as f:
        read_data = f.read()
        
    start = time.time()
    _ = loads_func(read_data)
    load_time = time.time() - start
    
    print(f"Serialize (dumps): {dump_time:.4f} seconds")
    print(f"Deserialize (loads): {load_time:.4f} seconds")
    print(f"Total time: {dump_time + load_time:.4f} seconds")
    print(f"File size: {size:.2f} MB")

if __name__ == "__main__":
    test_lib("standard json", json.dumps, json.loads)
    
    if ujson:
        test_lib("ujson", ujson.dumps, ujson.loads)
    else:
        print("\nujson not installed.")
        
    if orjson:
        test_lib("orjson", orjson.dumps, orjson.loads, is_bytes=True)
    else:
        print("\norjson not installed.")
        
    if os.path.exists("test_bench.json"):
        os.remove("test_bench.json")
