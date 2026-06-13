import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import random

BASE_URL = "https://data-argo.ifremer.fr/dac/incois/"
TARGET_DIR = "data/raw"

def run():
    os.makedirs(TARGET_DIR, exist_ok=True)
    print("Fetching float list from INCOIS...")
    response = requests.get(BASE_URL)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all float directories (they are usually numbers ending with /)
    links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
    floats = [link for link in links if link.strip('/').isdigit() or (link[0].isalpha() and link[1:].strip('/').isdigit())]
    
    # Shuffle to get random floats
    random.shuffle(floats)
    
    downloaded = 0
    target_count = 20
    
    for float_dir in floats:
        if downloaded >= target_count:
            break
            
        float_id = float_dir.strip('/')
        float_url = urllib.parse.urljoin(BASE_URL, float_dir)
        
        try:
            r = requests.get(float_url)
            r.raise_for_status()
            fsoup = BeautifulSoup(r.text, 'html.parser')
            
            # Find the profile file, typically floatid_prof.nc or similar
            prof_links = [a.get('href') for a in fsoup.find_all('a') if a.get('href') and a.get('href').endswith('_prof.nc')]
            
            if not prof_links:
                continue
                
            prof_file = prof_links[0]
            prof_url = urllib.parse.urljoin(float_url, prof_file)
            
            # Check if file already exists
            local_path = os.path.join(TARGET_DIR, prof_file)
            if os.path.exists(local_path):
                print(f"Already have {prof_file}")
                downloaded += 1
                continue
                
            print(f"Downloading {prof_file}...")
            pr = requests.get(prof_url, stream=True)
            pr.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in pr.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            downloaded += 1
            print(f"Success! ({downloaded}/{target_count})")
            
        except Exception as e:
            print(f"Error fetching {float_id}: {e}")

if __name__ == "__main__":
    run()
