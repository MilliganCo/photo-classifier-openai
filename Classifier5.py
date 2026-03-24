import os
import openai
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import base64
import json
import shutil
import re

openai.api_key = "<OPENAI_API_KEY>"


def get_folder_path():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory()
    root.destroy()
    return folder


def encode_image(image_path):
    with open(image_path, "rb") as img:
        return base64.b64encode(img.read()).decode('utf-8')


def classify_images_with_gpt4(images_batch, retries=1, detect_color=False):
    if detect_color:
        prompt = """
        For the FIRST clothing image, identify the PRIMARY color in simple terms (e.g., Blue, Red, DarkGreen, Black).
        Also, classify EACH image STRICTLY into one of these categories:

        - "_Main": The ENTIRE model must be visible from head to feet WITHOUT cropping. The person may be standing or in a casual pose (e.g. leaning or hands in pockets), but as long as their FULL BODY is present in the frame — classify as "_Main". Pose or framing style does not matter. If the whole body is visible, it is ALWAYS "_Main".
    
        - "_Angle": Medium framing, approximately showing half or partial body (e.g., cropped at waist or thighs), or clearly emphasizing a particular pose or angle, but NOT showing the FULL BODY.
    
        - "_Detail": Close-up shot primarily focusing on a specific detail or part of the clothing item, such as fabric texture, stitches, pockets, labels, cuffs, etc.

        Respond ONLY with valid JSON:
        {
          "color": "DetectedColor",
          "classifications": [{"view_type": "_Main"}, {"view_type": "_Angle"}, ...]
        }
        """
    else:
        prompt = """
        Classify EACH clothing image STRICTLY into one of these categories:

        - "_Main": The ENTIRE model must be visible from head to feet WITHOUT cropping. The person may be standing or in a casual pose (e.g. leaning or hands in pockets), but as long as their FULL BODY is present in the frame — classify as "_Main". Pose or framing style does not matter. If the whole body is visible, it is ALWAYS "_Main".
    
        - "_Angle": Medium framing, approximately showing half or partial body (e.g., cropped at waist or thighs), or clearly emphasizing a particular pose or angle, but NOT showing the FULL BODY.
    
        - "_Detail": Close-up shot primarily focusing on a specific detail or part of the clothing item, such as fabric texture, stitches, pockets, labels, cuffs, etc.

        Respond ONLY with valid JSON array matching the order:
        [{"view_type": "_Main"}, {"view_type": "_Angle"}, ...]
        """

    encoded_images = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(img)}"}}
                      for img in images_batch]

    client = openai.OpenAI(api_key=openai.api_key)

    for attempt in range(retries + 1):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}] + encoded_images}],
            max_tokens=400
        )

        content = response.choices[0].message.content.strip()

        # Удаление markdown-обёртки ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if match:
            content = match.group(1).strip()

        try:
            result = json.loads(content)

            if detect_color:
                if "color" not in result or "classifications" not in result:
                    raise ValueError("Incorrect format or missing keys.")
                classifications = [item["view_type"] for item in result["classifications"]]
                return result["color"], classifications
            else:
                classifications = [item["view_type"] for item in result]
                return classifications

        except (json.JSONDecodeError, ValueError) as e:
            if attempt == retries:
                print(f"❌ Ошибка после {retries + 1} попыток. Последний ответ: {content}")
                default_result = ["_NotClassified"] * len(images_batch)
                return ("unknown", default_result) if detect_color else default_result
            else:
                print(f"⚠️ Некорректный ответ GPT-4o ({e}), попытка {attempt + 1}/{retries + 1}. Повторный запрос...")


def build_new_filename(view_type, color="unknown", barcode="0000000000000", extra_feature="_Model", angle_number=1, image_index=1):
    return f"{barcode}{view_type}{extra_feature}_{angle_number}_{color}_{image_index}.jpg"


def main():
    folder = get_folder_path()
    if not folder:
        return

    backup_folder = os.path.join(folder, "renamed_files")
    os.makedirs(backup_folder, exist_ok=True)

    files = sorted([f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))])

    detected_color = None

    batch_size = 10
    for batch_start in range(0, len(files), batch_size):
        batch_files = files[batch_start:batch_start + batch_size]
        full_paths = [os.path.join(folder, f) for f in batch_files]

        if detected_color is None:
            detected_color, view_types = classify_images_with_gpt4(full_paths, detect_color=True)
        else:
            view_types = classify_images_with_gpt4(full_paths)

        for idx, (original_name, view_type) in enumerate(zip(batch_files, view_types), batch_start + 1):
            new_filename = build_new_filename(view_type=view_type, color=detected_color, image_index=idx)
            new_full_path = os.path.join(backup_folder, new_filename)

            shutil.copy2(os.path.join(folder, original_name), new_full_path)
            print(f"{original_name} → {new_filename}")

    print(f"✅ Готово! Переименованные файлы сохранены в: {backup_folder}")


if __name__ == "__main__":
    main()
