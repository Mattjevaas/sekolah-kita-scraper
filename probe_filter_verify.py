import urllib.request
import json
import ssl

# Ignore SSL errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

CARI_ENDPOINT = "https://sekolah.data.kemendikdasmen.go.id/v1/sekolah-service/sekolah/cari-sekolah"

def post_json(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
        return {}

# Verify comma-separated filter results
print("Testing filter: 'TK,KB'")
res = post_json(CARI_ENDPOINT, {"page": 0, "size": 10, "keyword": "", "kabupaten_kota": "Kota Bandung", "bentuk_pendidikan": "TK,KB"})
items = res.get('data', [])
print(f"Returned {len(items)} items.")
for item in items:
    print(f"  - {item.get('bentuk_pendidikan')}")

# Verify full list
full_filter = "KB,MAK,PAUDQ,RA,SPKTK,SPKPG,SPS,TK,TKLB,TPA"
print(f"\nTesting full filter: {full_filter}")
res_full = post_json(CARI_ENDPOINT, {"page": 0, "size": 10, "keyword": "", "kabupaten_kota": "Kota Bandung", "bentuk_pendidikan": full_filter})
items_full = res_full.get('data', [])
print(f"Returned {len(items_full)} items.")
for item in items_full:
    print(f"  - {item.get('bentuk_pendidikan')}")
