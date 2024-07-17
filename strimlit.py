from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

# Fungsi untuk mengubah halaman menjadi tampilan yang lebih menarik


def set_page_layout():
    st.markdown(
        """
        <style>
        .reportview-container {
            background: linear-gradient(135deg, #f3ec78 0%, #af4261 100%);
            color: #333333;
        }
        .sidebar .sidebar-content {
            background: linear-gradient(135deg, #232526 0%, #414345 100%);
            color: #ffffff;
        }
        .sidebar .sidebar-content .stButton>button {
            background-color: #64dfdf;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            transition: background-color 0.3s;
        }
        .sidebar .sidebar-content .stButton>button:hover {
            background-color: #5bb6b6;
            cursor: pointer;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Fungsi untuk menggambar diagram dan menampilkan tabel


def draw_charts(df):
    # Konversi kolom tanggal ke format datetime
    df['date'] = pd.to_datetime(df['date'])

    # Group by tanggal dan jenis_kendaraan dan sum masuk and keluar counts
    summary = df.groupby(['date', 'jenis_kendaraan']).sum().reset_index()

    # Grafik batang vertikal dengan kategori dan tahun
    fig_bar_vertical = go.Figure()
    categories = summary['jenis_kendaraan'].unique()
    for category in categories:
        filtered_data = summary[summary['jenis_kendaraan'] == category]
        fig_bar_vertical.add_trace(go.Bar(
            x=filtered_data['date'],
            y=filtered_data['masuk'],
            name=f'{category} Masuk'
        ))
        fig_bar_vertical.add_trace(go.Bar(
            x=filtered_data['date'],
            y=filtered_data['keluar'],
            name=f'{category} Keluar'
        ))

    fig_bar_vertical.update_layout(
        title='Jumlah Kendaraan Masuk dan Keluar per Tanggal',
        xaxis_title='Tanggal',
        yaxis_title='Jumlah Kendaraan',
        barmode='group'
    )

    st.plotly_chart(fig_bar_vertical)

    # Pie chart for masuk counts
    total_masuk = summary.groupby('jenis_kendaraan')[
        'masuk'].sum().reset_index()
    fig_pie_masuk = px.pie(total_masuk, names='jenis_kendaraan', values='masuk',
                           title='Distribusi Kendaraan Masuk', height=400)
    st.plotly_chart(fig_pie_masuk)

    # Pie chart for keluar counts
    total_keluar = summary.groupby('jenis_kendaraan')[
        'keluar'].sum().reset_index()
    fig_pie_keluar = px.pie(total_keluar, names='jenis_kendaraan', values='keluar',
                            title='Distribusi Kendaraan Keluar', height=400)
    st.plotly_chart(fig_pie_keluar)

    # Scatter plot masuk vs keluar
    fig_scatter = px.scatter(summary, x='masuk', y='keluar', color='jenis_kendaraan',
                             title='Perbandingan Jumlah Kendaraan Masuk dan Keluar',
                             labels={'masuk': 'Jumlah Kendaraan Masuk', 'keluar': 'Jumlah Kendaraan Keluar'})
    st.plotly_chart(fig_scatter)

    # Line chart for vehicle counts by date
    fig_line = px.line(summary, x='date', y='masuk', color='jenis_kendaraan',
                       title='Jumlah Kendaraan Masuk per Tanggal',
                       labels={'date': 'Tanggal', 'masuk': 'Jumlah Kendaraan Masuk'})
    st.plotly_chart(fig_line)

    # Histogram for masuk counts
    fig_hist = px.histogram(summary, x='date', y='masuk', color='jenis_kendaraan',
                            title='Histogram Jumlah Kendaraan Masuk per Tanggal',
                            labels={'date': 'Tanggal', 'masuk': 'Jumlah Kendaraan Masuk'})
    st.plotly_chart(fig_hist)

    # Horizontal bar chart for masuk counts
    fig_hbar = px.bar(total_masuk, x='masuk', y='jenis_kendaraan', orientation='h',
                      title='Jumlah Kendaraan Masuk per Jenis Kendaraan',
                      labels={'masuk': 'Jumlah Kendaraan Masuk', 'jenis_kendaraan': 'Jenis Kendaraan'})
    st.plotly_chart(fig_hbar)

    st.write("### Total Objek Terdeteksi")
    st.table(summary.drop(columns=['_id']))

# Fungsi untuk menampilkan data history


def show_history(history_df, date_filter):
    if history_df.empty:
        st.write("Belum ada data history yang tersimpan.")
    else:
        st.write("### History")

        # Apply date filter
        if date_filter == '1 Hari':
            filter_date = datetime.now() - timedelta(days=1)
        elif date_filter == '3 Hari':
            filter_date = datetime.now() - timedelta(days=3)
        elif date_filter == '7 Hari':
            filter_date = datetime.now() - timedelta(days=7)
        elif date_filter == '1 Bulan':
            filter_date = datetime.now() - timedelta(days=30)
        else:
            filter_date = datetime.min

        history_df['Tanggal'] = pd.to_datetime(history_df['Tanggal'])
        filtered_history_df = history_df[history_df['Tanggal'] >= filter_date]

        if filtered_history_df.empty:
            st.write(f"Tidak ada data history untuk {date_filter} terakhir.")
        else:
            for index, row in filtered_history_df.iterrows():
                if st.button(f"Hapus Baris {index}"):
                    history_df.drop(index, inplace=True)
                    history_df.to_csv('history.csv', index=False)
                    st.success(f"Baris {index} berhasil dihapus dari history.")
                st.write(f"#### Tanggal: {row['Tanggal']}")
                st.write(f"**Kategori**: {row['Kategori']}")
                st.write(f"**Masuk**: {row['Masuk']}")
                st.write(f"**Keluar**: {row['Keluar']}")

                # Menampilkan visualisasi di dalam sidebar history
                filtered_summary = pd.DataFrame({
                    'jenis_kendaraan': [row['Kategori']],
                    'masuk': [row['Masuk']],
                    'keluar': [row['Keluar']]
                })

                fig = px.bar(filtered_summary, x='jenis_kendaraan', y=['masuk', 'keluar'],
                             title='Jumlah Kendaraan Masuk dan Keluar',
                             labels={'value': 'Jumlah', 'variable': 'Status'},
                             barmode='group', height=300)
                st.plotly_chart(fig)

# Fungsi untuk mengambil data dari MongoDB


def load_data_from_mongodb():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["rrk_jenis_kendaraan"]
    collection = db["hasil_deteksi"]
    data = list(collection.find())
    for document in data:
        document['_id'] = str(document['_id'])
    df = pd.DataFrame(data)
    return df


# Set tata letak halaman dan warna latar belakang
set_page_layout()

option = st.sidebar.selectbox(
    'Silakan pilih:',
    ('Home', 'Dataframe', 'History')
)

if option == 'Home' or option == '':
    st.title("Selamat Datang di Halaman Utama")
    st.write("Di sini Anda dapat memilih untuk melihat data atau visualisasi.")
elif option == 'Dataframe':
    st.title("Dataframe")
    try:
        df = load_data_from_mongodb()
        draw_charts(df)
        if st.button('Simpan Data Visualisasi ke History'):
            st.write("Data visualisasi berhasil disimpan ke history.")
    except Exception as e:
        st.error(f"Gagal mengambil data dari MongoDB: {e}")
elif option == 'History':
    st.title("History")
    try:
        history_df = pd.read_csv('history.csv')
    except FileNotFoundError:
        history_df = pd.DataFrame(
            columns=['Tanggal', 'Kategori', 'Masuk', 'Keluar'])

    date_filter = st.selectbox('Filter berdasarkan waktu:', [
                               'Semua', '1 Hari', '3 Hari', '7 Hari', '1 Bulan'])
    show_history(history_df, date_filter)
