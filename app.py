import os
from datetime import datetime
import cv2
import pandas as pd
from pymongo import MongoClient
from ultralytics import YOLO
from ultralytics.solutions import object_counter
from flask import Flask, jsonify, Response
import time  # import time for delay control

app = Flask(__name__)

# Function to detect whether a vehicle is IN or OUT based on its movement


def is_vehicle_in(current_box, previous_box):
    if previous_box and current_box[1] < previous_box[1]:
        return "IN"
    elif previous_box and current_box[1] > previous_box[1]:
        return "OUT"
    return None

# Function to update vehicle count based on their movement across ROI


def update_vehicle_count(tracks, region_of_interest, counts, model, previous_boxes):
    for track in tracks:
        for box in track.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            class_index = int(box.cls[0])
            class_name = model.names[class_index]

            # Check if the center point is within the ROI
            if region_of_interest[0][1] < center_y < region_of_interest[2][1]:
                status = is_vehicle_in(
                    [center_x, center_y], previous_boxes.get(class_name))
                if status:
                    counts[class_name][status.lower()] += 1
                    print(
                        f"Vehicle {class_name} moved {status} at ({center_x}, {center_y})")
                previous_boxes[class_name] = [center_x, center_y]
            else:
                print(
                    f"Vehicle {class_name} at ({center_x}, {center_y}) not in ROI")

# Function to save detection results to MongoDB


def save_to_mongodb(counts, collection):
    timestamp = datetime.now()
    for class_name, count in counts.items():
        document = {
            "jenis_kendaraan": class_name,
            "masuk": count['in'],
            "keluar": count['out'],
            "date": timestamp.strftime('%Y-%m-%d'),
            "hari": timestamp.strftime('%A')
        }
        collection.insert_one(document)
        print(f"Inserted document: {document}")

# Function to export data from MongoDB to CSV


def export_to_csv(collection):
    try:
        data = list(collection.find())
        if not data:
            print("No data found in MongoDB collection.")
            return

        df = pd.DataFrame(data)

        # Check if necessary columns are in dataframe
        required_columns = {'jenis_kendaraan',
                            'date', 'masuk', 'keluar', 'hari'}
        if not required_columns.issubset(df.columns):
            print(
                f"Required columns are missing from data: {required_columns - set(df.columns)}")
            return

        # Save results to CSV
        csv_file = 'hasil_deteksi_kendaraan.csv'
        df.to_csv(csv_file, index=False)
        print(f"Data has been exported to {csv_file}")

    except Exception as e:
        print(f"Error reading from MongoDB or exporting to CSV: {e}")


@app.route('/process_video', methods=['GET'])
def process_video():
    # Initialize MongoDB connection
    client = MongoClient('mongodb://localhost:27017/')
    db = client['rrk_jenis_kendaraan']
    collection = db['hasil_deteksi']

    # Initialize YOLO model
    try:
        model = YOLO('best.pt')
    except Exception as e:
        return jsonify({'error': f"Error loading model: {e}"}), 500

    # Path to the video file
    video_path = os.path.abspath('video2 (1).mp4')

    # OpenCV VideoCapture setup
    cap = cv2.VideoCapture(video_path)

    # Check if video capture is successful
    if not cap.isOpened():
        return jsonify({'error': "Error opening video file"}), 500

    # Define Region of Interest (ROI)
    region_of_interest = [(20, 560), (1700, 560), (1700, 604), (20, 604)]

    # Video writer setup
    output_file = "object_counting_output.avi"
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_writer = cv2.VideoWriter(
        output_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

    # Initialize Object Counter
    counter = object_counter.ObjectCounter()
    counter.set_args(view_img=True, reg_pts=region_of_interest,
                     classes_names=model.names, draw_tracks=True)

    # Dictionary to store counts of each vehicle class
    counts = {'car': {'in': 0, 'out': 0}, 'truck': {'in': 0, 'out': 0}}

    # Dictionary to store previous bounding boxes of each vehicle class
    previous_boxes = {}

    # Process frames
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Error reading video stream or file")
            break

        # Perform object tracking using YOLO model
        results = model.track(frame, persist=True, show=False)
        frame = counter.start_counting(frame, results)
        video_writer.write(frame)

        # Update vehicle counts based on their movement across ROI
        update_vehicle_count(results, region_of_interest,
                             counts, model, previous_boxes)

        # Simulate delay to allow smoother streaming to Flutter
        time.sleep(0.05)  # Adjust the delay as needed

    # Release resources
    cap.release()
    video_writer.release()
    cv2.destroyAllWindows()

    # Save detection results to MongoDB
    save_to_mongodb(counts, collection)

    # Export data from MongoDB to CSV
    export_to_csv(collection)

    return jsonify({'message': 'Processing complete', 'counts': counts})


def generate():
    cap = cv2.VideoCapture('object_counting_output.avi')
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        (flag, encodedImage) = cv2.imencode(".jpg", frame)
        if not flag:
            continue
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')


@app.route('/stream_video', methods=['GET'])
def stream_video():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    # Menjalankan aplikasi Flask pada port 5001
    app.run(host='0.0.0.0', port=5001)
