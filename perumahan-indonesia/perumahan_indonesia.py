from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
import time
import re

# BROWSER
def setup_driver():
    options = Options()
    options.add_argument("--lang=id")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    # User Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# KOORDINAT
def extract_coordinates(url):
    try:
        # Pola 1: @lat,lon
        match1 = re.search(r'@([-0-9.]+),([-0-9.]+)', url)
        if match1: return float(match1.group(1)), float(match1.group(2))
            
        # Pola 2: !3dlat!4dlon
        match2_lat = re.search(r'!3d([-0-9.]+)', url)
        match2_lon = re.search(r'!4d([-0-9.]+)', url)
        if match2_lat and match2_lon: return float(match2_lat.group(1)), float(match2_lon.group(1))
        
    except: return 0.0, 0.0
    return 0.0, 0.0

# SCRAPING 
def scrape_housing_indonesia(target_total=3000):
    driver = setup_driver()
    all_data = []
    
    # DAFTAR KOTA DI INDONESIA 
    cities = [
        # SUMATERA
        "Medan", "Pekanbaru", "Palembang", "Bandar Lampung", "Batam",
        # JAWA (Barat, Tengah, Timur)
        "Tangerang", "Bekasi", "Bogor", "Karawang", "Bandung", 
        "Cirebon", "Semarang", "Solo", "Yogyakarta", "Surabaya", "Malang",
        # BALI & NUSA TENGGARA
        "Denpasar", "Mataram",
        # KALIMANTAN
        "Pontianak", "Balikpapan", "Samarinda", "Banjarmasin",
        # SULAWESI
        "Makassar", "Manado"
    ]
    
    keywords = ["Perumahan Subsidi", "Perumahan Elite"] 
    
    print(f"🇮🇩 MEMULAI PROYEK NASIONAL: PEMETAAN HUNIAN (Target: {target_total})...")
    print(f"   Mencakup {len(cities)} Kota Besar di Indonesia.")
    
    for city in cities:
        for key in keywords:
            if len(all_data) >= target_total: 
                print("🎉 Target tercapai! Berhenti scraping.")
                break
            
            # Reset Browser (Cuci Otak) agar data kota tidak bocor
            driver.get("about:blank")
            time.sleep(1)
            
            # Construct URL
            search_query = f"{key} di {city}"
            url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            
            print(f"\n📍 [{city.upper()}] Sedang mencari: '{search_query}'...")
            driver.get(url)
            
            try:
                wait = WebDriverWait(driver, 20)
                scrollable_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
                
                # Jeda 
                time.sleep(3) 
                
                print(f"   ⏳ Scrolling data...")
                for i in range(15): 
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                    time.sleep(1.5)
                
                # Ambil Link
                results = driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
                
                count_local = 0
                for item in results:
                    link = item.get_attribute("href")
                    name = item.get_attribute("aria-label")
                    
                    if not link or not name: continue
                    
                    lat, lon = extract_coordinates(link)
                    
                    if lat != 0.0:
                        all_data.append({
                            'pulau_kota': city,
                            'kategori': 'Subsidi' if 'Subsidi' in key else 'Elite',
                            'nama_perumahan': name,
                            'latitude': lat,
                            'longitude': lon,
                            'link_gmaps': link
                        })
                        count_local += 1
                
                print(f"      ✅ Berhasil ambil {count_local} data.")
                
            except Exception as e:
                print(f"      ⚠️ Gagal di {city}: {e}")
                
        if len(all_data) >= target_total: break

    driver.quit()
    print(f"\n🎉 SELESAI! Total Data Terkumpul: {len(all_data)}")
    return pd.DataFrame(all_data)

# VISUALISASI PETA INDONESIA
def create_map(df, filename_csv):
    if df.empty: return
    print("🎨 Membuat Peta Indonesia...")
    
    df = df.drop_duplicates(subset=['latitude', 'longitude'])
    
    # Peta Indonesia
    m = folium.Map(location=[-2.5, 118.0], zoom_start=5, tiles="CartoDB positron")
    
    #Marker Cluster
    marker_cluster = MarkerCluster(name="Titik Perumahan").add_to(m)
    
    for _, row in df.iterrows():
        color = 'green' if row['kategori'] == 'Subsidi' else 'red'
        
        popup_txt = f"""
        <b>{row['nama_perumahan']}</b><br>
        Lokasi: {row['pulau_kota']}<br>
        Tipe: {row['kategori']}
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_txt, max_width=200)
        ).add_to(marker_cluster)

    # Heatmap
    heat_data = df[['latitude', 'longitude']].values.tolist()
    HeatMap(heat_data, radius=10, blur=15, name="Heatmap Pembangunan").add_to(m)
    
    folium.LayerControl().add_to(m)
    
    map_filename = filename_csv.replace(".csv", ".html")
    m.save(map_filename)
    print(f"✅ Peta Siap! Buka file: {map_filename}")

# MAIN
if __name__ == "__main__":

    df_hasil = scrape_housing_indonesia(target_total=3000)
    
    if not df_hasil.empty:
        nama_file = "data_perumahan_indonesia_raya.csv"
        df_hasil.to_csv(nama_file, index=False)
        print(f"💾 Data disimpan: {nama_file}")
        
        create_map(df_hasil, nama_file)
    else:
        print("❌ Data kosong.")