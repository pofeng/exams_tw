import csv
import subprocess

csv_file_path = "url.csv"

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
    "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",  # corrected User-Agent string
    'sec-ch-ua: "Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "sec-ch-ua-mobile: ?0",
    'sec-ch-ua-platform: "Linux"',
]

try:
    with open(csv_file_path, mode="r", encoding="utf-8") as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)  # 讀取標題列並略過

        for row in csv_reader:
            # 讀取每一列的資料，並去除雙引號
            exam_year = row[0].strip('"')
            exam_code = row[1].strip('"')
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

            # 題庫與答案的Folder
            question_bank_folder = f"question_bank"

            # 檢查試題網址和答案網址是否為空
            if question_url:
                question_filename = f"{question_bank_folder}/{exam_code}_{category_code}_{session}_Q.pdf"
                curl_command_question = ["curl", "-o", question_filename, question_url]
                # 加入 header 參數
                for h in headers:
                    curl_command_question.extend(["-H", h])

                print(f"下載試題: {question_url} -> {question_filename}")
                subprocess.run(
                    curl_command_question, check=False
                )  # check=False 避免 curl 錯誤時終止程式

            if answer_url:
                answer_filename = f"{question_bank_folder}/{exam_code}_{category_code}_{session}_A.pdf"
                curl_command_answer = ["curl", "-o", answer_filename, answer_url]
                # 加入 header 參數
                for h in headers:
                    curl_command_answer.extend(["-H", h])

                print(f"下載答案: {answer_url} -> {answer_filename}")
                subprocess.run(
                    curl_command_answer, check=False
                )  # check=False 避免 curl 錯誤時終止程式
except FileNotFoundError:
    print(f"錯誤: 找不到檔案 '{csv_file_path}'")
except Exception as e:
    print(f"發生錯誤: {e}")
