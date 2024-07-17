import requests

# URL dari API yang telah Anda buat
api_url = "http://192.168.1.10:5001/process_video"

try:
    # Mengirim permintaan GET ke API
    response = requests.get(api_url)

    # Memeriksa apakah permintaan berhasil (status code 200)
    if response.status_code == 200:
        # Menampilkan hasil dari API
        print("Response from API:")
        print(response.json())
    else:
        print(f"Failed to access API. Status code: {response.status_code}")
        print("Response content:")
        print(response.text)

except requests.exceptions.RequestException as e:
    # Menangani pengecualian yang mungkin terjadi selama permintaan
    print(f"Error accessing API: {e}")
