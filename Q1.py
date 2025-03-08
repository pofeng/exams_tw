import re
import subprocess

def extract_questions_from_pdf(file_path):
    """
    從指定 PDF 檔案路徑的檔案中提取問題、題號和選項。

    Args:
        file_path (str): 要提取問題的 PDF 檔案路徑。

    Returns:
        list: 包含問題、題號和選項的列表，每個元素都是一個字典，
              包含 'number' (題號)、'question' (問題文字) 和 'choices' (選項列表) 三個鍵。
    """

    questions = []
    try:
        # 使用 pdf2text 提取 PDF 內容
        result = subprocess.run(['pdftotext', '-layout', file_path, '-'], capture_output=True, text=True)
        content = result.stdout

        # 使用正則表達式尋找題號、問題和選項，允許題號後方出現空格
        matches = re.findall(r'(\d+)\.\s*([^\n]+)([\s\S]*?(?=^\d+\.|\Z))', content, re.MULTILINE)
        for number, question, choices_text in matches:
            # 使用正則表達式提取選項，允許選項後方出現空格
            choices = re.findall(r'[A-D]\.\s*([^\n]+)', choices_text)
            questions.append({'number': number, 'question': question, 'choices': choices})
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except FileExistsError:
        print(f"Error: pdftotext not found. Please install poppler-utils.")
    return questions

# 提取 "Q1.pdf" 檔案中的問題、題號和選項
questions = extract_questions_from_pdf("Q1.pdf")

# 顯示所有題號、問題、選項
for q in questions:
    print(f"題號 {q['number']}: {q['question']}")
    print(f"選項: {q['choices']}")
