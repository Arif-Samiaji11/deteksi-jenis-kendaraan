import os
from ultralytics import YOLO
from ultralytics.solutions import object_counter
import cv2
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Fungsi untuk mendeteksi kendaraan IN berdasarkan lintasan


def is_vehicle_in(current_box, previous_box):
    # Asumsi bahwa arah gerakan dari bawah ke atas dianggap sebagai IN
    if previous_box and current_box[1] < previous_box[1]:
        return True
    return False

# Fungsi untuk menyimpan hasil deteksi ke MongoDB


def save_to_mongodb(detections, collection):
    if detections:
        try:
            collection.insert_many(detections)
            print(f"Inserted {len(detections)} records into MongoDB.")
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")

# Fungsi untuk mengambil data dari MongoDB dan menyimpannya ke CSV


def export_to_csv(collection):
    try:
        data = list(collection.find())
        if not data:
            print("No data found in MongoDB collection.")
            return

        df = pd.DataFrame(data)
        required_columns = {'jenis_kendaraan', 'date', 'deteksi', 'hari'}
        if not required_columns.issubset(df.columns):
            print(
                f"Required columns are missing from data: {required_columns - set(df.columns)}")
            return

    except Exception as e:
        print(f"Error reading from MongoDB: {e}")
        return

    # Hitung jumlah deteksi per jenis kendaraan per hari
    deteksi_per_hari = df.groupby(['date', 'jenis_kendaraan']).agg({
        'deteksi': 'sum'
    }).reset_index()

    # Simpan hasil ke CSV
    csv_file = 'hasil_deteksi_kendaraan.csv'
    deteksi_per_hari.to_csv(csv_file, index=False)
    print(f"Data has been exported to {csv_file}")


# Inisialisasi koneksi MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['db_datak']
collection = db['hasil_deteksi']

# Inisialisasi model YOLO
try:
    model = YOLO('best.pt')
except Exception as e:
    print(f"Error loading model: {e}")
    exit()

# Path video yang akan digunakan (gunakan jalur absolut)
video_path = os.path.abspath('video2 (1).mp4')

# Check if video file exists
if not os.path.exists(video_path):
    print(f"Video file '{video_path}' not found.")
    exit()

# Buka file video
cap = cv2.VideoCapture(video_path)
assert cap.isOpened(), "Error opening video file"

# Dapatkan informasi video
w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH,
             cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

region_of_interest = [(20, 600), (1700, 604), (1700, 560), (20, 560)]

# Video writer
video_writer = cv2.VideoWriter(
    "object_counting_output.avi", cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

# Init Object Counter
counter = object_counter.ObjectCounter()
counter.set_args(view_img=True, reg_pts=region_of_interest,
                 classes_names=model.names, draw_tracks=True)

frame_count = 0
previous_boxes = {}
detections = []

# Proses setiap frame
while cap.isOpened():
    success, im0 = cap.read()
    if not success:
        print("Video frame is empty or video processing has been successfully completed.")
        break
    tracks = model.track(im0, persist=True, show=False)
    im0 = counter.start_counting(im0, tracks)
    video_writer.write(im0)
    frame_count += 1

    # Kumpulkan data deteksi
    for prediction in tracks:
        for i, box in enumerate(prediction.boxes):
            current_box = box.xyxy[0].tolist()
            if is_vehicle_in(current_box, previous_boxes.get(i)):
                class_index = int(box.cls[0])
                class_name = model.names[class_index]
                timestamp = datetime.now()
                document = {
                    "frame_number": frame_count,
                    "jenis_kendaraan": class_name,
                    "deteksi": 1,  # Setiap entri dihitung sebagai satu deteksi
                    "date": timestamp.strftime('%Y-%m-%d'),
                    "hari": timestamp.strftime('%A'),
                    "timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                detections.append(document)
            previous_boxes[i] = current_box

cap.release()
video_writer.release()
cv2.destroyAllWindows()

# Simpan semua data deteksi ke MongoDB
save_to_mongodb(detections, collection)

# Ekspor data ke CSV
export_to_csv(collection)
