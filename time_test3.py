"""Test if IPv6 vs IPv4 is causing the 2-second delay."""
import requests, time, socket

# Check what localhost resolves to
print("localhost resolves to:", socket.getaddrinfo('localhost', 5000))

sess = requests.Session()

# Test with explicit 127.0.0.1 (IPv4)
for i in range(3):
    t = time.time()
    r = sess.get('http://127.0.0.1:5000/health', timeout=5)
    print(f'127.0.0.1 [{i}]: {(time.time()-t)*1000:.0f}ms')

# Test with explicit [::1] (IPv6)
for i in range(2):
    t = time.time()
    try:
        r = sess.get('http://[::1]:5000/health', timeout=3)
        print(f'[::1] [{i}]: {(time.time()-t)*1000:.0f}ms  status={r.status_code}')
    except Exception as e:
        print(f'[::1] [{i}]: FAILED in {(time.time()-t)*1000:.0f}ms: {e}')

sess.close()
