import os
import openai
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

# 1. Устанавливаем ключ OpenAI:
openai.api_key = "<OPENAI_API_KEY>"

# 2. Подключаем Ultralytics YOLO
try:
    from ultralytics import YOLO
except ImportError:
    print("Необходимо установить ultralytics: pip install ultralytics")
    raise

# 3. Загружаем предобученную модель YOLOv8
#    (если нужна максимально точная - 'yolov8x.pt'; более лёгкая - 'yolov8s.pt'/'yolov8n.pt')
model_path = "yolov8x.pt"
model = YOLO(model_path)

def get_folder_path():
    """Открывает диалог выбора папки и возвращает путь к ней."""
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    root.destroy()
    return folder_selected

def detect_view_type_yolo(image_path: str) -> str:
    results = model.predict(source=image_path)
    if len(results) == 0 or len(results[0].boxes) == 0:
        return "_Detail"

    res = results[0]

    person_boxes = []
    orig_w, orig_h = res.orig_shape[1], res.orig_shape[0]

    for box in res.boxes:
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        if cls_id == 0:  # person
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            box_w = x2 - x1
            box_h = y2 - y1
            box_area = box_w * box_h
            img_area = orig_w * orig_h
            area_ratio = box_area / img_area
            aspect_ratio = box_h / box_w if box_w > 0 else 0

            # Проверка расстояния до границ
            margin_x = min(x1, orig_w - x2) / orig_w
            margin_y = min(y1, orig_h - y2) / orig_h

            person_boxes.append({
                "area_ratio": area_ratio,
                "aspect_ratio": aspect_ratio,
                "margin_x": margin_x,
                "margin_y": margin_y,
                "conf": conf
            })

    if not person_boxes:
        return "_Detail"

    # Сортируем по уверенности и площади одновременно
    person_boxes.sort(key=lambda x: (x["conf"], x["area_ratio"]), reverse=True)
    best_box = person_boxes[0]

    # Новая логика:
    if best_box["area_ratio"] < 0.45:
        return "_Main"
    elif best_box["area_ratio"] < 0.75 and best_box["aspect_ratio"] > 1.2:
        # Обычно портрет/средний план — это вертикальный формат bounding box
        return "_Angle"
    else:
        # Проверяем дополнительное условие: очень крупный план или горизонтальный bounding box
        if best_box["aspect_ratio"] <= 1.2 or best_box["area_ratio"] >= 0.75:
            return "_Detail"

    # Если не сработало ничего — вернем Angle (более нейтральное)
    return "_Angle"

def classify_image_with_openai(image_path: str) -> dict:
    """
    1) Анализируем изображение моделью YOLOv8, чтобы определить примерный вид (ракурс).
    2) Передаём полученный ракурс в ChatGPT, чтобы сгенерировать JSON-ответ с нужными полями.
       При этом "view_type" не даём GPT менять.
    """

    # 1) Определяем предполагаемый ракурс
    view_type_suggestion = detect_view_type_yolo(image_path)

    # 2) Формируем prompt, где чётко говорим: «view_type не менять!»
    prompt = f"""
    You are an assistant that classifies product images.
    The user has an image with a garment or detail.
    We used YOLOv8 detection and determined the shot type is {view_type_suggestion}.

    Generate JSON with the following keys:
      1) "barcode": guess if there's an EAN-like code (or set a default);
      2) "view_type": EXACTLY "{view_type_suggestion}" — do NOT alter this field;
      3) "extra_feature": one of ["","_Model","_Interior","_Street","_Sample"] (optional);
      4) "color": guess the main color;
      5) "angle_number": if relevant;
      6) "image_index": a sequential number in the set.

    IMPORTANT:
    - The "view_type" key must remain exactly "{view_type_suggestion}".
    - Do not change or rename that field.
    - Please fill the other fields as needed.

    Example final JSON:
    {{
       "barcode": "4601234567890",
       "view_type": "{view_type_suggestion}",
       "extra_feature": "",
       "color": "black",
       "angle_number": 1,
       "image_index": 1
    }}
    """

    response = openai.chat.completions.create(
        model="gpt-4",  # или "gpt-3.5-turbo", если GPT-4 недоступен
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    import json
    try:
        classification_result = json.loads(content)
    except json.JSONDecodeError:
        # На случай, если ChatGPT не вернул JSON
        classification_result = {
            "barcode": "4601234567890",
            "view_type": view_type_suggestion,
            "extra_feature": "",
            "color": "black",
            "angle_number": 1,
            "image_index": 1
        }

    # Дополнительно: если GPT всё же упорно поменяло "view_type",
    # можно вручную переопределить обратно:
    classification_result["view_type"] = view_type_suggestion

    return classification_result

def build_new_filename(classification: dict) -> str:
    """
    Формируем итоговое имя файла в формате: 4601234567890_Main_1_black_1.jpg
    """
    barcode = classification.get("barcode", "4600000000000")
    view_type = classification.get("view_type", "_Main")
    extra_feature = classification.get("extra_feature", "")
    angle_number = classification.get("angle_number", 1)
    color = classification.get("color", "black")
    image_index = classification.get("image_index", 1)

    # Если extra_feature есть, дополним "_"
    if extra_feature and not extra_feature.startswith("_"):
        extra_feature = "_" + extra_feature

    new_filename = f"{barcode}{view_type}{extra_feature}_{angle_number}_{color}_{image_index}.jpg"
    return new_filename

def make_unique_filename(folder_path: str, base_name: str) -> str:
    """
    Проверяем, нет ли такого имени. Если есть, то добавляем _2, _3 и т.д.
    """
    name, ext = os.path.splitext(base_name)
    candidate = base_name
    counter = 2
    while os.path.exists(os.path.join(folder_path, candidate)):
        candidate = f"{name}_{counter}{ext}"
        counter += 1
    return candidate

def main():
    folder_path = get_folder_path()
    if not folder_path:
        print("Папка не выбрана. Завершение программы.")
        return

    valid_extensions = (".jpg", ".jpeg", ".png", ".webp")
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]

    if not files:
        print("В выбранной папке нет изображений.")
        return

    root = tk.Tk()
    root.withdraw()

    for file_name in files:
        old_full_path = os.path.join(folder_path, file_name)

        # 1) Классифицируем изображение (YOLO + ChatGPT)
        classification_result = classify_image_with_openai(old_full_path)

        # 2) Формируем новое имя
        new_file_name = build_new_filename(classification_result)

        # 3) Убираем символы, не разрешённые в Windows
        invalid_chars = r'\/:*?"<>|'
        for ch in invalid_chars:
            new_file_name = new_file_name.replace(ch, "_")

        # 4) Избегаем конфликтов имён
        new_file_name = make_unique_filename(folder_path, new_file_name)

        # 5) Собираем итоговый путь
        new_full_path = os.path.join(folder_path, new_file_name)
        new_full_path = os.path.normpath(new_full_path)

        # 6) Спрашиваем пользователя
        msg = (
            f"Исходное имя файла: {file_name}\n"
            f"Предлагаемое имя: {new_file_name}\n\n"
            f"Переименовать?"
        )
        answer = messagebox.askyesno("Переименование файла", msg)

        if answer:
            try:
                os.rename(old_full_path, new_full_path)
                print(f"Файл {file_name} переименован в {new_file_name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось переименовать файл:\n{e}")
        else:
            print(f"Переименование {file_name} отменено пользователем.")

    root.destroy()

if __name__ == "__main__":
    main()
