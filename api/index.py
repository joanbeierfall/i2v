from flask import Flask, request, jsonify
import os
import json
import random
import base64
import mimetypes
import requests
from urllib.parse import urlparse
from PIL import Image
import io
from asgiref.wsgi import WsgiToAsgi
asgi_app = WsgiToAsgi(app)


app = Flask(__name__)

# Global variables
fotortoken = None
user_id = None
bearer_token = None

SOURCE_VIDEOS = {
    "Funk Music": "/fvideo/uploads/default/20240718/738207682066153472.mp4",
    "Opera": "/fvideo/uploads/default/20240716/737550736009695232.mp4"
}

def register_clipfly_account():
    global fotortoken, user_id, bearer_token
    remote_json_url = "http://temp-gmail.site/clipfly_users.json"
    try:
        response = requests.get(remote_json_url)
        response.raise_for_status()
        users = response.json()
        valid_users = [u for u in users if int(u.get("credit", 0)) > 0]
        if not valid_users:
            raise Exception("No valid users with credit > 0.")
        user = random.choice(valid_users)
        fotortoken = user["fotortoken"]
        user_id = user["user_id"]
        bearer_token = user["token"]
        print(f"✅ Loaded user: {user['email']}")
    except Exception as e:
        raise Exception(f"Failed to load user data: {str(e)}")

def upload_base64_image(image_path, name, token, fotortoken):
    with open(image_path, "rb") as f:
        image_data = f.read()
        base64_str = base64.b64encode(image_data).decode("utf-8")

    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/jpeg"
    data_uri = f"data:{mime_type};base64,{base64_str}"

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Platform": "web",
        "X-Country": "IN",
        "Zone": "330",
        "Origin": "https://www.clipfly.ai",
        "Referer": "https://www.clipfly.ai/aitools/scene?c=all"
    }
    cookies = {"fotortoken": fotortoken}
    payload = {
        "content": data_uri,
        "name": name,
        "file_type": "image",
        "is_original_name": 0,
        "prefix_path": "/uploads"
    }
    url = "https://www.clipfly.ai/api/v1/common/upload/base64"
    response = requests.post(url, headers=headers, cookies=cookies, json=payload)
    response.raise_for_status()
    res_json = response.json()
    if res_json.get("code") == 0:
        return res_json["data"]["storage_path"]
    else:
        raise Exception(f"Upload failed: {res_json.get('message')}")

def create_material(url_path, thumb_path, token, fotortoken):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Platform": "web",
        "X-Country": "IN",
        "Zone": "330",
        "Origin": "https://www.clipfly.ai",
        "Referer": "https://www.clipfly.ai/aitools/scene?c=all"
    }
    cookies = {"fotortoken": fotortoken}
    payload = {
        "is_ai": -1,
        "urls": {"url": url_path, "thumb": thumb_path},
        "name": "clipfly.jpeg",
        "type": "image",
        "attrs": {"width": 1080, "height": 1920}
    }
    url = "https://www.clipfly.ai/api/v1/user/materials/create"
    response = requests.post(url, headers=headers, cookies=cookies, json=payload)
    response.raise_for_status()
    res_json = response.json()
    if res_json.get("code") == 0:
        return res_json["data"]["id"]
    else:
        raise Exception(f"Material error: {res_json.get('message')}")

def create_ai_task(material_id, image_url, token, fotortoken, prompt, style_id, task_type=19):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Platform": "web",
        "X-Country": "IN",
        "Zone": "330",
        "Origin": "https://www.clipfly.ai",
        "Referer": "https://www.clipfly.ai/aitools/scene?c=all"
    }
    cookies = {"fotortoken": fotortoken}
    payload = {
        "type": task_type,
        "attrs": [{
            "styleId": style_id,
            "urls": {"url": image_url},
            "materialId": material_id,
            "prompt": prompt,
            "is_scale": 0,
            "c": "all",
            "subTitle": ""
        }]
    }
    url = "https://www.clipfly.ai/api/v1/user/ai-task-queues"
    response = requests.post(url, headers=headers, cookies=cookies, json=payload)
    response.raise_for_status()
    res_json = response.json()
    if res_json.get("code") == 0 and res_json["data"].get("tasks"):
        return res_json["data"]["tasks"][0]["id"]
    else:
        raise Exception(f"Task creation error: {res_json.get('message')}")

@app.route("/image_to_video", methods=["POST"])
def image_to_video():
    try:
        register_clipfly_account()
        image_file = request.files["image"]
        prompt = request.form.get("prompt", "")
        style_id = request.form.get("style_id", "1")
        image_path = "temp_uploaded_image.jpg"
        image_file.save(image_path)

        storage_path = upload_base64_image(image_path, "main.jpeg", bearer_token, fotortoken)
        thumb_path = upload_base64_image(image_path, "thumb.jpeg", bearer_token, fotortoken)
        material_id = create_material(storage_path, thumb_path, bearer_token, fotortoken)
        task_id = create_ai_task(material_id, storage_path, bearer_token, fotortoken, prompt, style_id)

        return jsonify({
            "status_code": 200,
            "task_id": task_id,
            "token": bearer_token,
            "member_id": user_id,
            "fotortoken": fotortoken
        })

    except Exception as e:
        return jsonify({"status_code": 500, "error": str(e)})

@app.route("/check_status", methods=["POST"])
def check_status():
    data = request.get_json()
    task_id = data.get("task_id")
    token = data.get("token")
    member_id = data.get("member_id")

    try:
        headers = {
            "Authorization": token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Platform": "web",
            "X-Country": "IN",
            "Zone": "330"
        }
        cookies = {"fotortoken": member_id}
        url = f"https://www.clipfly.ai/api/v1/user/ai-tasks/{task_id}"
        res = requests.get(url, headers=headers, cookies=cookies)
        data = res.json()
        if data.get("code") != 0:
            return jsonify({"status_code": 400, "error": data.get("message")})
        video_url = data["data"]["after_material"]["urls"]["url"]
        return jsonify({"status_code": 200, "video_url": f"https://www.clipfly.ai{video_url}"})
    except Exception as e:
        return jsonify({"status_code": 500, "error": str(e)})

@app.route("/create_video", methods=["POST"])
def create_video():
    try:
        image_file = request.files["image"]
        selected_video_label = request.form.get("music", "Funk Music")
        image_path = "temp_upload.jpg"
        image_file.save(image_path)
        filename = os.path.basename(image_path)

        auth_url = "http://temp-gmail.site/clipfly_users.json"
        response = requests.get(auth_url)
        response.raise_for_status()
        auths = response.json()
        valid_auths = [a for a in auths if int(a.get("credit", 0)) > 0]
        auth = random.choice(valid_auths)

        # Upload base64
        mime_type, _ = mimetypes.guess_type(image_path)
        with open(image_path, "rb") as f:
            image_data = f.read()
        base64_str = base64.b64encode(image_data).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{base64_str}"

        headers = {
            "Authorization": auth["token"],
            "Content-Type": "application/json",
            "Platform": "web",
            "X-Country": "IN",
            "Zone": "330"
        }
        cookies = {"fotortoken": auth["fotortoken"]}

        upload_payload = {
            "content": data_uri,
            "name": filename,
            "file_type": "image",
            "is_original_name": 0,
            "prefix_path": "/uploads"
        }
        res = requests.post("https://www.clipfly.ai/api/v1/common/upload/base64", headers=headers, cookies=cookies, json=upload_payload)
        res_json = res.json()
        uploaded_url = res_json["data"]["url"]

        # Register material
        parsed_sign = urlparse(uploaded_url)
        material_payload = {
            "urls": {"url": parsed_sign.path, "thumb": parsed_sign.path},
            "from_ai": 1,
            "name": os.path.splitext(filename)[0]
        }
        res = requests.post("https://www.clipfly.ai/api/v1/user/materials/create", headers=headers, cookies=cookies, json=material_payload)
        material_id = res.json()["data"]["id"]

        # AI task
        task_payload = {
            "materialId": material_id,
            "urls": {"url": parsed_sign.path},
            "source_video": SOURCE_VIDEOS.get(selected_video_label),
            "type": 15
        }
        res = requests.post("https://www.clipfly.ai/api/v1/user/ai-tasks", headers=headers, cookies=cookies, json=task_payload)
        task_id = res.json()["data"]["id"]

        return jsonify({
            "status_code": 200,
            "task_id": task_id,
            "token": auth["token"],
            "member_id": auth["fotortoken"]
        })

    except Exception as e:
        return jsonify({"status_code": 500, "error": str(e)})

asgi_app = WsgiToAsgi(app)
if __name__ == "__main__":
    app.run(debug=True)
