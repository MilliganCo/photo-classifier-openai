import os
import openai
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import base64
import json

# ваш API ключ OpenAI
openai.api_key = "<OPENAI_API_KEY>"


def get_folder_path():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory()
    root.destroy()
    return folder


# GPT-4 Vision API запрос
def classify_with_gpt4_vision(image_path, retries=1):
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

    prompt = """
    Classify this clothing image STRICTLY into one of these categories based on the framing and visibility of the model or clothing item:

    - "_Main": The ENTIRE model is visible from head to feet, fully showing the clothing item. Even if the model is turned sideways, as long as the FULL BODY (head, torso, arms, legs, feet) is clearly visible without cropping, classify as "_Main".
    
    - "_Angle": Medium framing, approximately showing half or partial body (e.g., cropped at waist or thighs), or clearly emphasizing a particular pose or angle, but NOT showing the FULL BODY.
    
    - "_Detail": Close-up shot primarily focusing on a specific detail or part of the clothing item, such as fabric texture, stitches, pockets, labels, cuffs, etc.
    
    Respond ONLY with a valid JSON format (without ANY additional text or explanations).  
    Example response:
    
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
        view_type = classify_with_gpt4_vision(full_path)

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
