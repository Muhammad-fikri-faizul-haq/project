import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Dashboard Persebaran Perumahan",
    page_icon="🏠",
    layout="wide"
)

# 2. FUNGSI LOAD DATA
@st.cache_data
def load_data():
    try:
        # Membaca file data perumahan
        df = pd.read_csv("data_perumahan_v2.csv")
        return df
    except FileNotFoundError:
        return None

# Eksekusi Load Data
df = load_data()

# 3. KONDISI UTAMA: CEK APAKAH DATA ADA
if df is not None:
    # --- SIDEBAR (FILTER) ---
    st.sidebar.title("🔍 Filter Data")
    
    # A. FILTER KOTA
    st.sidebar.subheader("📍 Lokasi")
    all_cities = sorted(df['pulau_kota'].unique().tolist())

    # Fungsi Callback untuk tombol Select/Clear All
    def update_city_selection(status):
        for city in all_cities:
            st.session_state[f"city_{city}"] = status

    with st.sidebar.expander("Pilih Kota", expanded=True):
        col_a, col_b = st.columns(2)
        col_a.button("Select All", key="all_city_btn", on_click=update_city_selection, args=(True,))
        col_b.button("Clear All", key="none_city_btn", on_click=update_city_selection, args=(False,))
        
        selected_cities = []
        for city in all_cities:
            key_name = f"city_{city}"
            if key_name not in st.session_state:
                st.session_state[key_name] = True
            if st.checkbox(city, key=key_name):
                selected_cities.append(city)

    # B. FILTER KATEGORI
    st.sidebar.subheader("🏷️ Kategori")
    all_categories = sorted(df['kategori'].unique().tolist())
    
    def update_cat_selection(status):
        for cat in all_categories:
            st.session_state[f"cat_{cat}"] = status

    with st.sidebar.expander("Pilih Jenis Perumahan", expanded=True):
        col_c, col_d = st.columns(2)
        col_c.button("Select All", key="all_cat_btn", on_click=update_cat_selection, args=(True,))
        col_d.button("Clear All", key="none_cat_btn", on_click=update_cat_selection, args=(False,))

        selected_categories = []
        for cat in all_categories:
            key_name = f"cat_{cat}"
            if key_name not in st.session_state:
                st.session_state[key_name] = True
            if st.checkbox(cat, key=key_name):
                selected_categories.append(cat)

    # PROSES FILTERING
    if not selected_cities or not selected_categories:
        st.warning("⚠️ Mohon pilih setidaknya satu Kota dan Kategori.")
        filtered_df = pd.DataFrame(columns=df.columns)
    else:
        filtered_df = df[
            (df['pulau_kota'].isin(selected_cities)) & 
            (df['kategori'].isin(selected_categories))
        ]

    # --- 4. MAIN DASHBOARD ---
    st.title("🏠 Housing Market Tracker")
    st.markdown("Data perumahan subsidi & elite di Indonesia.")

    # Tampilan Metric
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Data Perumahan", f"{len(filtered_df)} Unit")
    col2.metric("Jumlah Kota Terpantau", f"{filtered_df['pulau_kota'].nunique()} Kota")
    
    if not filtered_df.empty:
        top_cat = filtered_df['kategori'].mode()[0]
        col3.metric("Kategori Terbanyak", top_cat)
    else:
        col3.metric("Kategori Terbanyak", "-")

    st.divider()

    # Tab Layout
    tab1, tab2, tab3 = st.tabs(["📊 Visualisasi Grafik", "🗺️ Peta GIS", "📄 Data Tabel"])

    with tab1:
        st.subheader("Analisis Statistik")
        if not filtered_df.empty:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.write("**Distribusi Perumahan per Kota**")
                fig, ax = plt.subplots(figsize=(8, 5))
                sns.countplot(data=filtered_df, x='pulau_kota', hue='kategori', palette='viridis', ax=ax)
                plt.xticks(rotation=45)
                st.pyplot(fig)
            with col_chart2:
                st.write("**Persentase Kategori**")
                fig2, ax2 = plt.subplots(figsize=(6, 6))
                count_data = filtered_df['kategori'].value_counts()
                ax2.pie(count_data, labels=count_data.index, autopct='%1.1f%%', startangle=90)
                st.pyplot(fig2)
        else:
            st.info("Tidak ada data untuk ditampilkan.")

    with tab2:
        st.subheader("Peta Persebaran Lokasi")
        if not filtered_df.empty:
            m = folium.Map(location=[filtered_df['latitude'].mean(), filtered_df['longitude'].mean()], zoom_start=10)
            marker_cluster = MarkerCluster().add_to(m)
            for _, row in filtered_df.iterrows():
                color = 'green' if row['kategori'] == 'Subsidi' else 'red'
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"{row['nama_perumahan']} ({row['kategori']})",
                    icon=folium.Icon(color=color)
                ).add_to(marker_cluster)
            st_folium(m, width="100%", height=500)
        else:
            st.warning("Data lokasi tidak tersedia.")

    with tab3:
        st.subheader("Data Tabel Terfilter")
        st.dataframe(filtered_df, use_container_width=True)
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name='data_filtered.csv', mime='text/csv')

else:
    st.error("⚠️ File 'data_perumahan_v2.csv' tidak ditemukan. Pastikan file CSV ada di folder yang sama.")