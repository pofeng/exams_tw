from dotenv import load_dotenv
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai
from google.genai import types
import pathlib
from pydantic import BaseModel
from typing import List
from pathlib import Path
import requests
import logging

# 設定日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(Path().absolute().parent, "exams_tw", "logs", "generation.log")
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
load_dotenv()

# model_name = "gemini-2.5-pro-preview-03-25"
model_name = "gemini-2.5-pro-exp-03-25"
modle_name_for_answer = "gemini-2.0-flash"


# genai is for direct call Google GenAI API
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# 定義PreMMLU Dataset格式
class PreMMLUDatasetItem(BaseModel):
    no: int
    question: str
    choices: List[str]


class MMLUDatasetItem(BaseModel):
    question: str
    choices: List[str]
    answer: str


class PreAnswerItem(BaseModel):
    no: int
    answer: str


client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

logger.info("初始化完成")


def resolve_question_from_pdf(file_path: str) -> list[PreMMLUDatasetItem]:
    """
    解析題目卷

    此函數負責將PDF格式的題目卷轉換為結構化的PreMMLUDatasetItem列表。

    Args:
        file_path: PDF檔案的路徑字串

    Returns:
        list[PreMMLUDatasetItem]: 包含題目、選項等資訊的結構化資料列表
    """
    logger.info(f"開始解析題目卷: {file_path}")

    # 建立完整的檔案路徑
    # 使用pathlib.Path來處理跨平台的檔案路徑問題
    file = pathlib.Path(
        os.path.join(
            os.path.dirname(os.path.abspath(".")),  # 獲取上層目錄的絕對路徑
            file_path,  # 加入檔案相對路徑
        )
    )
    logger.debug(f"完整檔案路徑: {file}")

    # 定義Prompt，指示AI模型如何解析PDF內容並轉換為特定格式
    prompt = """
    Please recognize the content of the file and extract the content of the file, then recompose the content into json format,
    the format should match MMLU Dataset format.
    """

    logger.info(f"使用模型 {model_name} 解析PDF內容")
    try:
        # 呼叫Google GenAI API進行內容生成
        # 將PDF檔案內容和Prompt一起傳送給模型
        response = client.models.generate_content(
            model=model_name,  # 使用預設的模型
            contents=[
                # 將PDF檔案轉換為bytes並指定MIME類型
                types.Part.from_bytes(
                    data=file.read_bytes(), mime_type="application/pdf"
                ),
                prompt,  # 加入Prompt指導模型如何處理內容
            ],
            config={
                "response_mime_type": "application/json",  # 指定回應的MIME類型為JSON
                "response_schema": list[PreMMLUDatasetItem],  # 指定回應應符合的資料結構
                # "max_output_tokens": 8096,  # 最大輸出token數（目前已註解）
            },
        )

        # 記錄 token 使用量
        logger.info(
            f"Token 使用量 - 輸入: {response.usage_metadata.prompt_token_count}, 輸出: {response.usage_metadata.candidates_token_count}, 總計: {response.usage_metadata.total_token_count}"
        )

        # 將回應文字解析為JSON格式
        result = json.loads(response.text)
        logger.info(f"成功解析題目卷，共獲取 {len(result)} 個題目")
        return result
    except Exception as e:
        logger.error(f"解析題目卷時發生錯誤: {e.__class__.__name__}: {str(e)}")
        if result:
            logger.info(f"response.text: {response.text}")
        raise


def resolve_answer_from_pdf(file_path: str) -> list[PreAnswerItem]:
    """
    解析答案卷PDF檔案，並將內容轉換為結構化的PreAnswerItem列表

    Args:
        file_path (str): 答案卷PDF檔案的路徑

    Returns:
        list[PreAnswerItem]: 包含題號和答案的結構化資料列表
    """
    logger.info(f"開始解析答案卷: {file_path}")

    # 建立完整的檔案路徑
    # 使用pathlib.Path來處理跨平台的檔案路徑問題
    file = pathlib.Path(
        os.path.join(
            os.path.dirname(os.path.abspath(".")),  # 獲取上層目錄的絕對路徑
            file_path,  # 加入檔案相對路徑
        )
    )
    logger.debug(f"答案卷完整檔案路徑: {file}")

    # 定義Prompt，指示AI模型如何解析PDF內容並轉換為特定格式
    # 這裡特別指示模型只解析題號和答案，並符合PreAnswerItem格式
    prompt = """
    Please recognize the content of the file and extract the content of the file, then recompose the content into json format,
    you shold follow the rules below:
    1. only parse the question number and answer, and the format should match PreAnswerItem format.
    2. the question number should be in the format of "題號: 題目"
    3. the answer should be in the format of "答案: 答案"
    4. Just put # sign in the answer field if you recognize the answer is # or cannot recognize the answer.
    """

    logger.info(f"使用模型 {modle_name_for_answer} 解析答案卷PDF內容")
    try:
        # 呼叫Google GenAI API進行內容生成
        # 將PDF檔案內容傳送給模型進行處理
        response = client.models.generate_content(
            model=modle_name_for_answer,  # 使用專門處理答案的模型
            contents=[
                # 將PDF檔案轉換為bytes並指定MIME類型
                types.Part.from_bytes(
                    data=file.read_bytes(), mime_type="application/pdf"
                ),
                prompt,  # 加入Prompt指導模型如何處理內容
            ],
            config={
                "response_mime_type": "application/json",  # 指定回應的MIME類型為JSON
                "response_schema": list[PreAnswerItem],  # 指定回應應符合的資料結構
            },
        )

        # 記錄 token 使用量
        logger.info(
            f"Token 使用量 - 輸入: {response.usage_metadata.prompt_token_count}, 輸出: {response.usage_metadata.candidates_token_count}, 總計: {response.usage_metadata.total_token_count}"
        )

        # 將回應文字解析為JSON格式
        result = json.loads(response.text)
        logger.info(f"成功解析答案卷，共獲取 {len(result)} 個答案項目")
        return result
    except Exception as e:
        logger.error(f"解析答案卷時發生錯誤: {e.__class__.__name__}: {str(e)}")
        raise


def merge_question_and_answer(
    questions: list[PreMMLUDatasetItem], answers: list[PreAnswerItem]
) -> list[PreMMLUDatasetItem]:
    """
    合併題目和答案

    此 function 將題目列表與答案列表進行配對合併，產生包含完整題目與答案的資料集。

    參數:
        questions: 包含題目資訊的列表，每個元素為 PreMMLUDatasetItem 型別
        answers: 包含答案資訊的列表，每個元素為 PreAnswerItem 型別

    返回:
        合併後的資料列表，每個元素包含題目資訊與對應的答案

    注意:
        - 此 function 假設 questions 與 answers 列表長度相同，且順序一一對應
        - 使用 Python 的解構語法 {**question, "answer": answer['answer']} 將答案合併到題目 dictionary 中
    """
    logger.info(
        f"開始合併題目與答案，題目數量: {len(questions)}，答案數量: {len(answers)}"
    )

    if len(questions) != len(answers):
        logger.error(
            f"題目數量({len(questions)})與答案數量({len(answers)})不一致，可能導致配對錯誤"
        )
        return []
    # 使用 list comprehension 與 dictionary unpacking 技術合併資料
    merged_data = [
        {**question, "answer": answer["answer"]}
        for question, answer in zip(questions, answers)
    ]

    # 移除每個項目中的 "no" 欄位
    for item in merged_data:
        if "no" in item:
            del item["no"]

    logger.info(f"題目與答案合併完成，共產生 {len(merged_data)} 筆完整資料")
    return merged_data


def download_file_if_not_exists(
    file_path: str, file_url: str, file_type: str = "檔案"
) -> bool:
    """
    檢查檔案是否存在，如果不存在或已毀損則從指定的 URL 下載

    Args:
        file_path (str): 目標檔案的路徑
        file_url (str): 檔案的下載 URL
        file_type (str): 檔案類型描述（用於日誌記錄）

    Returns:
        bool: 檔案是否成功下載或已存在且完好
    """
    file_corrupted = False

    # 檢查檔案是否存在且可讀取
    if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
        logger.warning(f"{file_type}不存在或無法存取: {file_path}")
        file_corrupted = True
    else:
        # 檢查檔案是否有毀損
        try:
            # 嘗試打開檔案以確認可讀取
            with open(file_path, "rb") as f:
                # 對於PDF檔案，可以嘗試讀取前幾個字節檢查是否為PDF格式
                if file_path.lower().endswith(".pdf"):
                    header = f.read(5)
                    if header != b"%PDF-":
                        logger.warning(
                            f"{file_type}可能已毀損: {file_path}，檔案頭部不是標準PDF格式"
                        )
                        file_corrupted = True

                # 檢查檔案大小是否為0
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    logger.warning(f"{file_type}可能已毀損: {file_path}，檔案大小為0")
                    file_corrupted = True

            if not file_corrupted:
                logger.info(f"{file_type}檢查完成，未發現明顯毀損: {file_path}")
                return True

        except Exception as e:
            logger.error(f"檢查{file_type}是否毀損時發生錯誤: {str(e)}")
            file_corrupted = True

    # 如果檔案不存在或已毀損，則嘗試下載
    if file_corrupted:
        if not file_url:
            logger.error(f"JSON 資料中未提供{file_type}網址，無法下載{file_type}")
            return False

        try:
            logger.info(f"嘗試從網址下載{file_type}: {file_url}")
            # 建立下載目錄
            download_dir = os.path.dirname(file_path)
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
                logger.info(f"已建立下載目錄: {download_dir}")

            # 下載檔案
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()  # 確認請求成功

            # 寫入檔案
            with open(file_path, "wb") as f:
                f.write(response.content)

            logger.info(f"成功下載{file_type}至: {file_path}")
            return True
        except Exception as e:
            logger.error(f"下載{file_type}時發生錯誤: {str(e)}")
            return False

    return True


if __name__ == "__main__":
    question_json_folder = os.path.join(
        Path().absolute().parent, "exams_tw", "question_json"
    )

    # 檢查資料夾是否存在
    if not os.path.exists(question_json_folder):
        logger.warning(f"資料夾不存在: {question_json_folder}")
        os.makedirs(question_json_folder)
        logger.info(f"已建立資料夾: {question_json_folder}")

    # 取得資料夾中所有的 JSON 檔案
    json_files = [f for f in os.listdir(question_json_folder) if f.endswith(".json")]
    json_files.sort()
    logger.info(f"在 {question_json_folder} 中找到 {len(json_files)} 個 JSON 檔案")

    # 迴圈處理每個 JSON 檔案
    for i, json_file in enumerate(json_files):
        file_path = os.path.join(question_json_folder, json_file)
        logger.info(f"正在處理檔案: {file_path}")

        # 測試用，只處理特定檔案
        if not json_file.endswith("fse00009968.json"):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # 檢查題庫是否已有足夠題目，如果已有足夠題目數量，表兆該檔案已正確處理過，應跳過
            if (
                "題庫" in json_data
                and isinstance(json_data["題庫"], list)
                and len(json_data["題庫"]) >= 20
            ):
                logger.info(
                    f"檔案 {json_file} 已有 {len(json_data['題庫'])} 題，跳過處理"
                )
                continue

            # 從 JSON 資料中取得試題檔案名稱，若不存在則返回空字串
            question_file_name = json_data.get("試題檔案", "")
            # 構建試題檔案的完整路徑
            question_file = os.path.join(
                Path().absolute().parent,
                "exams_tw",
                "question_bank",
                question_file_name,
            )

            # 從 JSON 資料中取得試題網址
            question_url = json_data.get("試題網址", "")

            # 下載試題檔案
            if not download_file_if_not_exists(question_file, question_url, "試題檔案"):
                continue

            logger.info(f"開始解析試題檔案: {question_file}")
            # 呼叫 function 解析 PDF 格式的試題檔案
            questions = resolve_question_from_pdf(question_file)
            logger.info(f"試題解析完成，共取得 {len(questions)} 個題目")

            # 從 JSON 資料中取得答案檔案名稱，若不存在則返回空字串
            answer_file_name = json_data.get("測驗式試題答案檔案", "")
            # 構建答案檔案的完整路徑
            answer_file = os.path.join(
                Path().absolute().parent,
                "exams_tw",
                "question_bank",
                answer_file_name,
            )

            # 從 JSON 資料中取得答案網址
            answer_url = json_data.get("測驗式試題答案網址", "")

            # 下載答案檔案
            if not download_file_if_not_exists(answer_file, answer_url, "答案檔案"):
                continue

            logger.info(f"開始解析答案卷: {answer_file}")
            # 呼叫 function 解析 PDF 格式的答案檔案
            answers = resolve_answer_from_pdf(answer_file)
            logger.info(f"答案解析完成，共取得 {len(answers)} 個答案")

            # 將解析出的題目與答案進行合併處理
            logger.info(f"開始合併題目與答案: 檔案 {json_file}")
            question_answers = merge_question_and_answer(questions, answers)
            logger.info(
                f"題目與答案合併完成，共產生 {len(question_answers)} 筆完整資料"
            )

            # 將處理好的題目與答案合併到 json_data 的題庫欄位中
            json_data["題庫"] = question_answers
            logger.info(
                f"已將 {len(question_answers)} 筆題目與答案資料合併至 JSON 檔案的題庫欄位"
            )

            # 將更新後的資料寫回原始 JSON 檔案
            # 使用 'w' 模式覆寫原檔案，ensure_ascii=False 確保中文字符正確顯示，indent=2 使 JSON 格式化便於閱讀
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"已將更新後的資料寫回檔案: {file_path}")

            logger.info(f"成功處理檔案: {json_file}")
        except Exception as e:
            logger.error(f"處理檔案 {json_file} 時發生錯誤: {str(e)}")
