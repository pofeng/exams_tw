import json
import os
import re
import pdfplumber
from PIL import Image, ImageOps
import io

## 適用於fse00000001~fse00000065

# 設定檔案路徑
QUESTION_JSON_DIR = "question_json"
QUESTION_BANK_DIR = "question_bank"
QUESTION_IMAGES_DIR = "question_images"


def ensure_dir_exists(dir_path):
    """
    確保目錄存在，如果不存在則創建
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def save_image(image_obj, pdf_name, page_num, img_num):
    """
    儲存圖片到指定目錄(僅處理JPEG/PNG/TIFF/GIF格式)
    """
    try:
        ensure_dir_exists(QUESTION_IMAGES_DIR)
        image_stream = image_obj["stream"].get_data()

        # 基本格式檢測
        file_format = None
        if image_stream.startswith(b"\xff\xd8"):
            file_format = "JPEG"
        elif image_stream.startswith(b"\x89PNG"):
            file_format = "PNG"
        elif image_stream.startswith(b"II*\x00") or image_stream.startswith(b"MM\x00*"):
            file_format = "TIFF"
        elif image_stream.startswith(b"GIF8"):
            file_format = "GIF"

        # 非指定格式直接跳過
        if not file_format:
            print(f"跳過非支援格式圖片：頁面 {page_num}, 圖片 {img_num}")
            return None

        # 構建檔案名稱
        image_filename = f"{pdf_name}_page{page_num}_img{img_num}.{file_format.lower()}"
        image_path = os.path.join(QUESTION_IMAGES_DIR, image_filename)

        # 統一處理流程
        try:
            from PIL import ImageFile

            ImageFile.LOAD_TRUNCATED_IMAGES = True

            with Image.open(io.BytesIO(image_stream)) as image:
                # 模式轉換
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")

                # 儲存參數
                save_args = {"format": file_format}
                if file_format == "JPEG":
                    save_args["quality"] = 90

                image.save(image_path, **save_args)
                print(f"成功儲存 {file_format} 圖片：{image_filename}")

                return {
                    "filename": image_filename,
                    "bbox": image_obj.get("bbox", [0, 0, 0, 0]),
                    "page": page_num,
                }

        except Exception as img_error:
            print(f"圖片處理失敗：{str(img_error)}")
            return None

    except Exception as e:
        print(f"儲存圖片時發生錯誤：{str(e)}")
        return None


def extract_answers_from_pdf(file_path):
    """
    從答案 PDF 檔案中提取答案。

    Args:
        file_path (str): 答案 PDF 檔案的路徑。

    Returns:
        list: 答案列表。
    """
    try:
        # 使用 pdfplumber 開啟並讀取 PDF
        with pdfplumber.open(file_path) as pdf:
            content = ""
            for page in pdf.pages:
                content += page.extract_text() + "\n"

        # 使用正則表達式找出所有答案（包含全形和半形字母）
        answers = re.findall(r"[ＡＢＣＤＡＢＣＤ]", content)

        # 移除可能的開頭標記（如果存在）
        if answers and answers[0] == "＃":
            answers.pop(0)

        return answers
    except Exception as e:
        print(f"解析答案檔案時發生錯誤：{str(e)}")
        return []


def extract_questions_from_pdf(file_path):
    """
    從指定 PDF 檔案路徑的檔案中提取問題、題號、選項和圖片。
    """
    questions = []
    pdf_name = os.path.splitext(os.path.basename(file_path))[0]
    content = ""
    questions_dict = {}  # 用於快速查找題目
    question_positions = {}  # 儲存題號的頁碼和TOP至頁底距離
    first_image_info = None  # 儲存第一張圖的資訊

    try:
        with pdfplumber.open(file_path) as pdf:
            # 第一次遍歷：收集所有文字內容、題號位置和圖片
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n處理第 {page_num} 頁")

                # 取得該頁的所有文字區塊
                words = page.extract_words()

                # 找出該頁所有題號的位置
                for word in words:
                    # 檢查是否為題號（例如：1.、2.、3. 等）
                    if re.match(r"^(\d+)\.", word["text"].strip()):
                        number = word["text"].split(".")[0]
                        # 儲存題號的頁碼和TOP至頁底距離
                        question_positions[number] = {
                            "page": page_num,
                            "top": word["top"],
                        }

                # 收集文字內容
                content += page.extract_text() + "\n"

            # 使用正則表達式找出所有題目
            matches = re.findall(
                r"(\d+)\.\s*([^\n]+)((?:(?!\n\d+\.).)*)", content, re.DOTALL
            )

            # 建立題目字典，儲存題目內容和選項
            for number, question, choices_text in matches:
                choices = re.findall(r"[A-D]\.\s*([^\n]+)", choices_text)
                questions_dict[number] = {
                    "number": number,
                    "question": question.strip(),
                    "choices": choices,
                    "images": [],
                }

            # 第二次遍歷：處理圖片
            for page_num, page in enumerate(pdf.pages, 1):
                if hasattr(page, "images") and page.images:
                    print(f"在第 {page_num} 頁找到 {len(page.images)} 張圖片")

                    # 處理每張圖片
                    for img_num, img in enumerate(page.images, 1):
                        print(f"\n處理第 {img_num} 張圖片")
                        print(f"\n圖片位置資訊：")
                        print(f"頁碼：{page_num}")
                        print(f"Y軸距離：{img['top']}")

                        image_info = save_image(img, pdf_name, page_num, img_num)

                        if image_info:
                            # 找出最適合的題目
                            target_question = None
                            max_matching_page = page_num  # 初始化為當前圖片的頁碼
                            max_matching_y = img["top"]  # 初始化為當前圖片的Y座標

                            # 遍歷所有題號位置
                            for number, pos in question_positions.items():
                                # 檢查題號是否在圖片所在頁之前，或在同一頁但TOP較小
                                if (pos["page"] < page_num) or (
                                    pos["page"] == page_num and pos["top"] <= img["top"]
                                ):
                                    # 逐步的更新最佳匹配
                                    if pos["page"] < max_matching_page or (
                                        pos["page"] == max_matching_page
                                        and pos["top"] < max_matching_y
                                    ):
                                        tmp_matching_page = pos["page"]
                                        tmp_matching_y = pos["top"]
                                        tmp_target_question = number

                            # 更新最佳匹配
                            max_matching_page = tmp_matching_page
                            max_matching_y = tmp_matching_y
                            target_question = tmp_target_question

                            # 如果找到對應題目，加入圖片
                            if target_question and target_question in questions_dict:
                                questions_dict[target_question]["images"].append(
                                    image_info["filename"]
                                )
                                print(
                                    f"將圖片 {image_info['filename']} 加入題目 {target_question}"
                                )

            # 轉換為列表形式
            questions = [q for q in questions_dict.values() if q["question"]]

            # 按題號排序
            questions.sort(key=lambda x: int(x["number"]))

            print(f"總共解析出 {len(questions)} 個題目")
            for q in questions:
                print(f"題號 {q['number']}: {len(q['images'])} 張圖片")

    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {file_path}")
    except Exception as e:
        print(f"錯誤：解析 PDF 時發生錯誤。\n錯誤訊息：{str(e)}")
        import traceback

        print(traceback.format_exc())

    return questions


def convert_answer_to_index(answer):
    """
    將答案字母（A、B、C、D）轉換為索引（0、1、2、3）

    Args:
        answer (str): 答案字母（可能是全形或半形）

    Returns:
        int: 答案在選項中的索引（0-based）
    """
    # 建立全形和半形字母對應的索引字典
    answer_map = {"A": 1, "B": 2, "C": 3, "D": 4, "Ａ": 1, "Ｂ": 2, "Ｃ": 3, "Ｄ": 4}
    return answer_map.get(answer, 0)  # 如果找不到對應，預設回傳 0


def process_exam_questions(json_filename: str = "fse00000001.json"):
    """
    處理考試題目的主要函數
    1. 讀取 JSON 檔案
    2. 取得對應的 PDF 檔案
    3. 解析 PDF 內容
    4. 解析答案
    5. 整合資訊並更新 JSON
    """
    # 讀取 JSON 檔案
    json_path = os.path.join(QUESTION_JSON_DIR, json_filename)
    print(f"開始處理 JSON 檔案：{json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            exam_data = json.load(f)

        # 取得試題和答案 PDF 檔案名稱
        question_pdf = exam_data.get("試題檔案")
        answer_pdf = exam_data.get("測驗式試題答案檔案")

        if not question_pdf or not answer_pdf:
            raise ValueError("找不到試題檔案或答案檔案欄位")

        # 組合完整的檔案路徑
        question_path = os.path.join(QUESTION_BANK_DIR, question_pdf)
        answer_path = os.path.join(QUESTION_BANK_DIR, answer_pdf)

        print(f"開始處理試題檔案：{question_pdf}")
        questions = extract_questions_from_pdf(question_path)

        print(f"開始處理答案檔案：{answer_pdf}")
        answers = extract_answers_from_pdf(answer_path)

        # 整合題目和答案
        question_bank = []
        for i, question in enumerate(questions):
            if i < len(answers):
                # 根據 schema 格式化題目資料
                question_data = {
                    "question": question["question"],
                    "images": question["images"],  # 使用該題目對應的圖片
                    "choices": question["choices"],
                    "answer": convert_answer_to_index(answers[i]),
                }
                question_bank.append(question_data)

        # 更新 JSON 檔案
        exam_data["題庫"] = question_bank

        # 寫回 JSON 檔案
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(exam_data, f, ensure_ascii=False, indent=2)

        # 輸出處理結果
        total_images = sum(len(q["images"]) for q in questions)
        print(f"\n成功處理 {len(question_bank)} 個題目")
        print(f"包含 {total_images} 張圖片")
        print(f"資料已更新至 {json_filename}")

    except FileNotFoundError as e:
        print(f"錯誤：{e}")
    except json.JSONDecodeError:
        print(f"錯誤：JSON 檔案格式不正確")
    except Exception as e:
        print(f"發生未預期的錯誤：{e}")


if __name__ == "__main__":
    for i in range(1, 66):
        process_exam_questions(f"fse{i:08d}.json")
