
import os
import openai
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

def get_folder_path():
    """Вызывает диалоговое окно для выбора папки и возвращает путь к ней."""
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    root.destroy()
    return folder_selected


import openai

openai.api_key = "<OPENAI_API_KEY>"


def classify_image_with_openai(image_path: str) -> dict:
    simulated_prompt = f"""
    You are an assistant that classifies product images.
    The user has an image of a garment or detail. 
    Suggest in JSON format:
    1) "barcode": guess if there's an EAN-like code (or set a default);
    2) "view_type": one of ["_Main","_Angle","_Material","_SizeChart","_Detail","_Pack","_Care","_Return","_Cross"];
    3) "extra_feature": one of ["","_Model","_Interior","_Street","_Sample"] (optional);
    4) "color": guess main color;
    5) "angle_number": if relevant;
    6) "image_index": a sequential number in the set.

    Example of final JSON:
    {{
       "barcode": "4601234567890",
       "view_type": "_Main",
       "extra_feature": "",
       "color": "black",
       "angle_number": 1,
       "image_index": 1
    }}
    """

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",  # или 'gpt-4', если у вас есть доступ
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": simulated_prompt},
        ],
        max_tokens=200,
        temperature=0
    )

    # Получаем ответ
    content = response.choices[0].message.content.strip()
    import json
    try:
        classification_result = json.loads(content)
    except json.JSONDecodeError:
        classification_result = {
            "barcode": "4601234567890",
            "view_type": "_Main",
            "extra_feature": "",
            "color": "black",
            "angle_number": 1,
            "image_index": 1
        }

    return classification_result


def build_new_filename(classification: dict) -> str:
    """
    Из словаря с классификацией формируем название файла в нужном формате:
    Пример: 4601234567890_Main_1_black_1.jpg
    """
    # Раскладываем поля
    barcode = classification.get("barcode", "4600000000000")
    view_type = classification.get("view_type", "_Main")
    extra_feature = classification.get("extra_feature", "")  # опционально, может быть пустой строкой
    angle_number = classification.get("angle_number", 1)
    color = classification.get("color", "black")
    image_index = classification.get("image_index", 1)

    # Формируем финальное имя файла
    # Обратите внимание, что extra_feature добавляем через "_" только если оно непустое
    extra_feature_str = extra_feature if extra_feature.startswith("_") else f"_{extra_feature}" if extra_feature else ""

    # Пример: 4601234567890_Main_1_black_1.jpg
    new_filename = f"{barcode}{view_type}{extra_feature_str}_{angle_number}_{color}_{image_index}.jpg"
    return new_filename


def main():
    # 1) Выбираем папку с изображениями
    folder_path = get_folder_path()
    if not folder_path:
        print("Папка не выбрана. Завершение программы.")
        return

    # 2) Перебираем все файлы в папке
    valid_extensions = (".jpg", ".jpeg", ".png", ".webp")
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]

    if not files:
        print("В выбранной папке нет изображений.")
        return

    # Создадим главное окно (не показываем пока), чтобы иметь возможность вызывать messagebox
    root = tk.Tk()
    root.withdraw()

    for file_name in files:
        old_full_path = os.path.join(folder_path, file_name)

        classification_result = classify_image_with_openai(old_full_path)
        new_file_name = build_new_filename(classification_result)

        # Удаляем/заменяем все недопустимые символы
        invalid_chars = r'\/:*?"<>|'
        for ch in invalid_chars:
            new_file_name = new_file_name.replace(ch, "_")

        new_full_path = os.path.join(folder_path, new_file_name)
        # Нормализуем путь (убирает двойные слэши и пр.)
        new_full_path = os.path.normpath(new_full_path)

        msg = f"Исходное имя: {file_name}\nПредлагаемое имя: {new_file_name}\n\nПереименовать?"
        answer = messagebox.askyesno("Переименование файла", msg)

        if answer:
            try:
                os.rename(old_full_path, new_full_path)
                print(f"Файл {file_name} переименован в {new_file_name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось переименовать файл:\n{e}")
        else:
            print(f"Переименование {file_name} отменено пользователем.")

    # Закрываем окно tkinter
    root.destroy()


if __name__ == "__main__":
    main()
