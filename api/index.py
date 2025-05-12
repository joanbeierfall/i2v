from flask import Flask, request, jsonify
from gradio_client import Client, handle_file

app = Flask(__name__)
client = Client("http://80.188.223.202:11115/")

# Face Dance endpoint
@app.route("/face_dance", methods=["POST"])
def run_face_dance():
    try:
        data = request.json
        image_url = data.get("image_url")
        video_label = data.get("video_label")

        result = client.predict(
            image_url=handle_file(image_url),
            selected_video_label=video_label,
            api_name="/face_dance_ui"
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Check Task endpoint
@app.route("/check_task_status", methods=["POST"])
def run_check_task():
    try:
        data = request.json
        task_id = data.get("task_id")
        token = data.get("token")
        member_id = data.get("member_id")

        result = client.predict(
            task_id=task_id,
            token=token,
            member_id=member_id,
            api_name="/check_task_status_ui"
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Image to Video endpoint
@app.route("/image_to_video", methods=["POST"])
def run_image_to_video():
    try:
        data = request.json
        image_url = data.get("image_url")
        style_id = data.get("style_id")
        prompt = style_id.capitalize()  # Style name used as prompt

        result = client.predict(
            image_url=handle_file(image_url),
            prompt=prompt,
            style_id=style_id,
            api_name="/image_to_video_ui"
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
