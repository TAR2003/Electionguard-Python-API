"""Diagnose the 2100ms latency."""
import requests, msgpack, time, socket

sess = requests.Session()
url = 'http://localhost:5000'

# Test 1: Health (small JSON response)
for i in range(3):
    t = time.time()
    r = sess.get(f'{url}/health', timeout=5)
    print(f'health [{i}]: {(time.time()-t)*1000:.0f}ms  {len(r.content)}bytes')

# Test 2: POST a minimal endpoint (if exists)
MSGPACK_HEADERS = {'Content-Type': 'application/msgpack', 'Accept': 'application/msgpack'}

# Test with tiny payload and tiny response
for i in range(3):
    payload = msgpack.packb({'ping': True}, use_bin_type=True)
    t = time.time()
    try:
        r = sess.post(f'{url}/health', data=payload, headers=MSGPACK_HEADERS, timeout=10)
        print(f'health POST [{i}]: {(time.time()-t)*1000:.0f}ms  {len(r.content)}bytes  {r.status_code}')
    except Exception as e:
        print(f'Error: {e}')

sess.close()

# Test TCP_NODELAY via raw socket to see if issue is IP stack
print("\nRaw TCP test (loopback):")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
s.settimeout(5)
t = time.time()
s.connect(('127.0.0.1', 5000))
s.sendall(b'GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n')
data = s.recv(4096)
print(f'Raw TCP GET: {(time.time()-t)*1000:.0f}ms  {len(data)}bytes')
s.close()
