import os
import urllib.request
import re
import ssl

def download_samples():
    base_url = "https://data-argo.ifremer.fr/dac/incois/"
    output_dir = "data/raw"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create an unverified SSL context to bypass CERTIFICATE_VERIFY_FAILED
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"Fetching float list from {base_url}...")
    req = urllib.request.Request(base_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch directory list: {e}")
        return

    links = re.findall(r'href="(\d+/)"', html)
    
    downloaded = 0
    for float_dir in links:
        if downloaded >= 3:
            break
            
        float_id = float_dir.strip('/')
        prof_url = f"{base_url}{float_dir}{float_id}_prof.nc"
        output_path = os.path.join(output_dir, f"{float_id}_prof.nc")
        
        print(f"Downloading {prof_url}...")
        try:
            req_prof = urllib.request.Request(prof_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_prof, context=ctx) as response, open(output_path, 'wb') as out_file:
                out_file.write(response.read())
            print(f"Saved to {output_path}")
            downloaded += 1
        except Exception as e:
            print(f"Failed to download {prof_url}: {e}")

if __name__ == "__main__":
    download_samples()
