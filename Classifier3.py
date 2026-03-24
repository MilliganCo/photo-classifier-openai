import os
import openai
import tkinter as tk
from tkinter import filedialog, messagebox
from ultralytics import YOLO
from PIL import Image
import base64
import json

# ваш API ключ OpenAI
openai.api_key = "<OPENAI_API_KEY>"

# YOLO модель
yolo_model = YOLO("yolov8x.pt")

def get_folder_path():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory()
    root.destroy()
    return folder

# Функция распознавания YOLO
def detect_with_yolo(image_path):
    results = yolo_model.predict(image_path, conf=0.5)[0]
    boxes = results.boxes.xyxy.tolist()
    classes = results.boxes.cls.tolist()
    person_boxes = [box for box, cls in zip(boxes, classes) if int(cls) == 0]
    return person_boxes

# GPT-4 Vision API запрос
def classify_with_gpt4_vision(image_path, retries=1):
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

    prompt = """
    Classify this clothing image strictly into one of these categories based on the framing of the image:

    - "_Main": Full body shot showing the entire model or clothing item clearly.
    - "_Angle": Medium shot showing approximately half of the body or clear pose.
    - "_Detail": Close-up detail focusing on a specific clothing part.

    Respond with a JSON ONLY (without ANY additional text, explanations, or formatting), for example:

    {"view_type": "_Main"}
    """

    client = openai.OpenAI(api_key=openai.api_key)

    for attempt in range(retries + 1):  # попытка повторного запроса при неудаче
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"}
                    }
                ]
            }],
            max_tokens=100
        )

        content = response.choices[0].message.content.strip()

        try:
            result = json.loads(content)
            if "view_type" in result:
                return result["view_type"]
            else:
                raise json.JSONDecodeError("Missing key 'view_type'", content, 0)
        except json.JSONDecodeError:
            # Если это была последняя попытка — выдаём стандартный результат
            if attempt == retries:
                print(f"❌ Ошибка парсинга JSON после {retries + 1} попыток. Последний ответ: {content}")
                return "_NotClassified"
            else:
                print(f"⚠️ Некорректный ответ GPT-4o, попытка {attempt + 1}/{retries + 1}. Повторный запрос...")


# Комбинированная логика YOLO + GPT-4 Vision
def determine_view_type(image_path):
    boxes = detect_with_yolo(image_path)

    if len(boxes) == 1:
        x1, y1, x2, y2 = boxes[0]
        box_area = (x2 - x1) * (y2 - y1)
        with Image.open(image_path) as im:
            img_area = im.width * im.height
        area_ratio = box_area / img_area

        # Обновлённые пороги:
        if area_ratio < 0.5:
            return "_Main"
        elif area_ratio < 0.7:
            return "_Angle"
        else:
            return "_Detail"

    # В случаях ошибки (несколько или ноль объектов):
    return classify_with_gpt4_vision(image_path)

def build_new_filename(view_type, color="unknown", barcode="0000000000000", extra_feature="_Model", angle_number=1, image_index=1):
    return f"{barcode}{view_type}{extra_feature}_{angle_number}_{color}_{image_index}.jpg"

def main():
    folder = get_folder_path()
    if not folder:
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    root = tk.Tk()
    root.withdraw()

    for idx, filename in enumerate(files, 1):
        full_path = os.path.join(folder, filename)
        view_type = determine_view_type(full_path)

        # Запрос подтверждения от пользователя
        new_filename = build_new_filename(view_type=view_type, image_index=idx)
        new_full_path = os.path.join(folder, new_filename)
        new_full_path = os.path.normpath(new_full_path)

        msg = f"Исходное имя: {filename}\nНовое имя: {new_filename}\nПереименовать?"
        if messagebox.askyesno("Подтверждение переименования", msg):
            os.rename(full_path, new_full_path)
            print(f"{filename} → {new_filename}")
        else:
            print(f"Пропущено: {filename}")

    root.destroy()

if __name__ == "__main__":
    main()
