"""Time just the HTTP round trip."""
import requests, msgpack, time

sess = requests.Session()
url = 'http://localhost:5000'

# Warmup
r = sess.get(f'{url}/health', timeout=5)
print('Health:', r.status_code)

MSGPACK_HEADERS = {'Content-Type': 'application/msgpack', 'Accept': 'application/msgpack'}
payload = {'number_of_guardians': 3, 'quorum': 2,
           'party_names': ['Alice','Bob'], 'candidate_names': ['Alice Johnson','Bob Smith']}

for i in range(5):
    packed = msgpack.packb(payload, use_bin_type=True, default=str)

    t_send = time.time()
    r = sess.post(f'{url}/setup_guardians', data=packed, headers=MSGPACK_HEADERS, timeout=30)
    http_t = time.time()-t_send

    t = time.time()
    result = msgpack.unpackb(r.content, raw=False)
    unpack_t = time.time()-t

    print(f'  [{i}] http={http_t*1000:.0f}ms  unpack={unpack_t*1000:.1f}ms  '
          f'resp={len(r.content):,}bytes  status={r.status_code}')
sess.close()
