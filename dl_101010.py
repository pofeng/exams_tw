import csv
import subprocess
import json
import os

csv_file_path = "url.csv"
sequence_counter = 1  # 用於生成序號

# 定義資料夾名稱
question_bank_folder = "question_bank"
question_json_folder = "question_json"

# 定義要加入的 header 參數
headers = [
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng",
    "Accept-Language: zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control: no-cache",
    "Connection: keep-alive",
    "Pragma: no-cache",
    "Sec-Fetch-Dest: document",
    "Sec-Fetch-Mode: navigate",
    "Sec-Fetch-Site: none",
    "Sec-Fetch-User: ?1",
    "Upgrade-Insecure-Requests: 1",
    "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    'sec-ch-ua: "Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "sec-ch-ua-mobile: ?0",
    'sec-ch-ua-platform: "Linux"',
]


def get_current_sequence():
    """取得目前的序號，不增加計數器"""
    global sequence_counter
    return f"fse{sequence_counter:08d}"


def increment_sequence():
    """增加序號計數器"""
    global sequence_counter
    sequence_counter += 1


def create_exam_json(row_data, question_filename, answer_filename):
    """建立符合schema的JSON資料"""
    current_sequence = get_current_sequence()
    exam_data = {
        "id": current_sequence,
        "考試年度": row_data[0],
        "考試代碼": row_data[1],
        "考試名稱": row_data[2],
        "等級代碼": row_data[3],
        "等級分類": row_data[4],
        "考試及等別": row_data[5],
        "類科代碼": row_data[6],
        "類科組別": row_data[7],
        "節次": row_data[8],
        "科目全名": row_data[9],
        "試題型態": row_data[10],
        "試題網址": row_data[11],
        "試題檔案": question_filename,
        "測驗式試題答案網址": row_data[12],
        "測驗式試題答案檔案": answer_filename,
        "備註": row_data[13],
        "題庫": [],  # 初始化為空列表
    }
    return exam_data


try:
    # 確保所需的資料夾都存在
    os.makedirs(question_bank_folder, exist_ok=True)
    os.makedirs(question_json_folder, exist_ok=True)

    with open(csv_file_path, mode="r", encoding="utf-8") as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)  # 讀取標題列並略過

        for row in csv_reader:
            # 讀取每一列的資料，並去除雙引號
            exam_year = row[0].strip('"')
            exam_code = row[1].strip('"')

            # 只處理考試代碼為101010的資料
            # if exam_code != "101010":
            #     continue

            exam_name = row[2].strip('"')
            level_code = row[3].strip('"')
            level_category = row[4].strip('"')
            exam_level = row[5].strip('"')
            category_code = row[6].strip('"')
            category_group = row[7].strip('"')
            session = row[8].strip('"')
            subject_name = row[9].strip('"')
            question_type = row[10].strip('"')
            question_url = row[11].strip('"')
            answer_url = row[12].strip('"')
            remark = row[13].strip('"')

            question_filename = None
            answer_filename = None

            # 下載試題
            if question_url:
                question_filename = f"{exam_code}_{category_code}_{session}_Q.pdf"
                full_question_path = f"{question_bank_folder}/{question_filename}"
                curl_command_question = ["curl", "-o", full_question_path, question_url]
                for h in headers:
                    curl_command_question.extend(["-H", h])

                print(f"下載試題: {question_url} -> {full_question_path}")
                subprocess.run(curl_command_question, check=False)

            # 下載答案
            if answer_url:
                answer_filename = f"{exam_code}_{category_code}_{session}_A.pdf"
                full_answer_path = f"{question_bank_folder}/{answer_filename}"
                curl_command_answer = ["curl", "-o", full_answer_path, answer_url]
                for h in headers:
                    curl_command_answer.extend(["-H", h])

                print(f"下載答案: {answer_url} -> {full_answer_path}")
                subprocess.run(curl_command_answer, check=False)

            # 如果成功下載了檔案，建立對應的JSON
            if question_filename or answer_filename:
                current_sequence = get_current_sequence()
                json_filename = f"{current_sequence}.json"
                full_json_path = f"{question_json_folder}/{json_filename}"
                exam_data = create_exam_json(row, question_filename, answer_filename)

                with open(full_json_path, "w", encoding="utf-8") as json_file:
                    json.dump(exam_data, json_file, ensure_ascii=False, indent=2)
                print(f"建立JSON檔案: {full_json_path}")

                # 在完整處理完一筆資料後才增加序號
                increment_sequence()

except FileNotFoundError:
    print(f"錯誤: 找不到檔案 '{csv_file_path}'")
except Exception as e:
    print(f"發生錯誤: {e}")
