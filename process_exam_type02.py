import json
import os
import re
import pdfplumber
from PIL import Image, ImageOps
import io
import util

## 適用以下條件的題庫
# 1.
# "公務人員初等考試" in fse.get("考試名稱", "")
# and fse.get("考試及等別", "") == "初等"
# and fse.get("等級分類", "").startswith("初等考試")
# and not fse.get("科目全名", "").startswith("公民與英文")

# 2.
# fse.get("等級分類", "") == "專技高考"
# and fse.get("類科組別", "") == "醫事檢驗師"
# and fse.get("考試代碼", "") == "101030", "101110", "102030"

# 3.
# fse00000122 ~ fse00000127

# 4.
# fse.get("考試及等別", "") == "高考中醫師"
# and fse.get("類科組別", "") == "中醫師"

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
        file_format = util.detect_image_format(image_obj)

        # 非指定格式直接跳過
        if not file_format:
            print(f"[{pdf_name}] 跳過非支援格式圖片：頁面 {page_num}, 圖片 {img_num}")
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
                print(f"[{pdf_name}] 成功儲存 {file_format} 圖片：{image_filename}")

                return {
                    "filename": image_filename,
                    "bbox": image_obj.get("bbox", [0, 0, 0, 0]),
                    "page": page_num,
                }

        except Exception as img_error:
            print(f"[{pdf_name}] 圖片處理失敗：{str(img_error)}")
            return None

    except Exception as e:
        print(f"[{pdf_name}] 儲存圖片時發生錯誤：{str(e)}")
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
        answers = re.findall(r"[ABCDEＡＢＣＤＥ]", content, re.DOTALL)

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

    try:
        with pdfplumber.open(file_path) as pdf:
            print(f"\n[{pdf_name}] 開始解析試題PDF")

            # 是否已經找到第1題題號
            is_first_hitted = False
            last_number = None

            # 第一次遍歷：收集所有文字內容、題號位置和圖片
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"[{pdf_name}] 處理第 {page_num} 頁")

                # 取得該頁的所有文字區塊
                words = page.extract_words()

                # 找出該頁所有題號的位置
                for word in words:
                    # 檢查是否為題號（例如：1.、2.、3. 等）
                    if re.match(
                        r"^(\d+)$", word["text"].strip()
                    ):  # 同時匹配全形(中文)和半形逗號
                        number = word["text"].split(".")[0]

                        # 如果第一次碰到疑似題號的文字，卻不是1，表示該文字不是題號，跳過
                        if not is_first_hitted:
                            if number == "1":
                                is_first_hitted = True
                            else:
                                continue

                        # 如果題號不是連續的，表示該文字不是題號，跳過
                        if last_number and int(number) != last_number + 1:
                            continue

                        last_number = int(number)

                        # 儲存題號的頁碼和TOP至頁底距離
                        question_positions[number] = {
                            "page": page_num,
                            "top": word["top"],
                        }
                # 收集文字內容
                content += page.extract_text() + "\n"

            # 移除題號前的錯誤換行符號
            # 將\n{數字}\n\ue18c 轉換為\n\ue18c
            content = re.sub(
                r"(?<=\n)(\d+)\n([\ue18c\ue18d\ue18e\ue18f])", r"\2", content
            )

            # 移除題號前的錯誤換行符號
            # 將\n2\n33轉換成\n33
            content = re.sub(r"(?<=\n)(\d+)\n(\d+)", r"\2", content)

            # 移除題號前的錯誤換行符號
            # 例如將\n2 2\n\ue18e轉換成\n\ue18e
            content = re.sub(
                r"(?<=\n)(\d+\s+\d+)\n([\ue18c\ue18d\ue18e\ue18f])", r"\2", content
            )

            # 移除題號前的錯誤換行符號
            # 例如將\n4 3\n63轉換成\n\63
            content = re.sub(r"(?<=\n)(\d+\s+\d+)\n(\d+)", r"\2", content)

            # 移除 代號：1102\n頁次：8－1 這樣的內容
            content = re.sub(r"代號：[^\n]+\n頁次：[^\n]+\n?", "", content)

            # 使用正則表達式找出所有題目
            matches = re.findall(
                r"(?sm)^\s*(\d+)\s+(.*?)(?=\n\ue18c)\s*((?:(?!^\s*\d+\s).)*)",
                content,
                re.DOTALL,
            )

            # 建立題目字典，儲存題目內容和選項
            for number, question, choices_text in matches:
                choices = re.findall(
                    r"(?sm)[\ue18c-\ue18f](.*?)(?=[\ue18c-\ue18f]|\Z)",
                    choices_text,
                )
                choices = [choice.strip() for choice in choices]
                questions_dict[number] = {
                    "number": number,
                    "question": question.strip(),
                    "choices": choices,
                    "images": [],
                }

            # 第二次遍歷：處理圖片
            for page_num, page in enumerate(pdf.pages, 1):
                if hasattr(page, "images") and page.images:
                    print(
                        f"[{pdf_name}] 在第 {page_num} 頁找到 {len(page.images)} 張圖片"
                    )

                    image_infos = util.compose_images(
                        page.images, page, pdf_name, page_num, QUESTION_IMAGES_DIR
                    )

                    for image_info in image_infos:
                        print(
                            f"[{pdf_name}] 處理第 {image_info['page']} 頁的圖片 {image_info['filename']}"
                        )

                        target_question = None
                        max_matching_page = page_num
                        max_matching_y = image_info["top"]

                        # 遍歷所有題號位置
                        for number, pos in question_positions.items():
                            # 檢查題號是否在圖片所在頁之前，或在同一頁但TOP較小
                            if (pos["page"] < page_num) or (
                                pos["page"] == page_num
                                and pos["top"] <= image_info["top"]
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
                                f"[{pdf_name}] 將圖片 {image_info['filename']} 加入題目 {target_question}"
                            )

            questions = [q for q in questions_dict.values() if q["question"]]

            # 按題號排序
            questions.sort(key=lambda x: int(x["number"]))

            print(f"[{pdf_name}] 總共解析出 {len(questions)} 個題目")
            for q in questions:
                print(f"[{pdf_name}] 題號 {q['number']}: {len(q['images'])} 張圖片")

    except FileNotFoundError:
        print(f"[{pdf_name}] 錯誤：找不到檔案 {file_path}")
    except Exception as e:
        print(f"[{pdf_name}] 錯誤：解析 PDF 時發生錯誤：{str(e)}")
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
    print(f"\n=== 開始處理 {json_filename} ===")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            exam_data = json.load(f)

        # 取得試題和答案 PDF 檔案名稱
        question_pdf = exam_data.get("試題檔案")
        answer_pdf = exam_data.get("測驗式試題答案檔案")

        if not question_pdf or not answer_pdf:
            raise ValueError(f"[{json_filename}] 找不到試題檔案或答案檔案欄位")

        # 組合完整的檔案路徑
        question_path = os.path.join(QUESTION_BANK_DIR, question_pdf)
        answer_path = os.path.join(QUESTION_BANK_DIR, answer_pdf)

        print(f"[{json_filename}] 開始處理試題檔案：{question_pdf}")
        questions = extract_questions_from_pdf(question_path)

        print(f"[{json_filename}] 開始處理答案檔案：{answer_pdf}")
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
        print(
            f"[{json_filename}] 成功處理 {len(question_bank)} 個題目，包含 {total_images} 張圖片"
        )
        print(f"[{json_filename}] 資料已更新至檔案")

    except FileNotFoundError as e:
        print(f"[{json_filename}] 錯誤：{e}")
    except json.JSONDecodeError:
        print(f"[{json_filename}] 錯誤：JSON 檔案格式不正確")
    except Exception as e:
        print(f"[{json_filename}] 發生未預期的錯誤：{e}")
    print(f"=== 完成處理 {json_filename} ===\n")


if __name__ == "__main__":
    # process_exam_questions(f"fse00000127.json")

    # for i in range(1, 66):
    #     process_exam_questions(f"fse{i:08d}.json")

    folder = os.path.join(QUESTION_JSON_DIR)
    json_files = [f for f in os.listdir(folder) if f.endswith(".json")]

    json_files.sort()  # 依檔名字母順序排序

    for json_file in json_files:
        process_exam_questions(json_file)
