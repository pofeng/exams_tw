import os
import shutil
import json
from dotenv import load_dotenv
from pymongo import MongoClient
import logging
from pathlib import Path

# 設定日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(Path().absolute().parent, "exams_tw", "logs", "update_db.log")
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

load_dotenv()


# 設定檔案路徑
QUESTION_JSON_DIR = "question_json"
QUESTION_JSON_DONE_DIR = "question_json_done"
QUESTION_BANK_DIR = "question_bank"
QUESTION_IMAGES_DIR = "question_images"
QUESTION_JSON_ALL_DIR = "question_json_all"
# 設定MongoDB連線
mongo_id = os.getenv("mongo_id")
mongo_pw = os.getenv("mongo_pw")

connection_url = f"mongodb+srv://{mongo_id}:{mongo_pw}@cluster0.lvdufzc.mongodb.net/"

client = MongoClient(connection_url)

db = client["freeseed"]

collection = db["exams"]

exams = collection.find()


def move_completed_files_to_done_dir():
    """
    將已處理完的JSON檔案移動到完成目錄

    此 function 負責將已經處理過的 JSON 檔案從來源目錄移動到完成目錄，
    以便於管理檔案狀態並避免重複處理。

    流程：
    1. 檢查並建立目標目錄（如不存在）
    2. 取得所有 JSON 檔案列表
    3. 逐一移動檔案並記錄操作
    """
    logger.info("開始執行檔案移動作業")

    # 確保目標目錄存在，若不存在則建立該目錄
    if not os.path.exists(QUESTION_JSON_DONE_DIR):
        logger.info(f"目標目錄 {QUESTION_JSON_DONE_DIR} 不存在，正在建立...")
        os.makedirs(QUESTION_JSON_DONE_DIR)
        logger.info(f"已成功建立目標目錄 {QUESTION_JSON_DONE_DIR}")

    # 使用 list comprehension 取得所有 JSON 檔案
    # 篩選條件為檔名必須以 .json 結尾
    json_files = [f for f in os.listdir(QUESTION_JSON_DIR) if f.endswith(".json")]
    logger.info(f"找到 {len(json_files)} 個 JSON 檔案需要移動")

    # 逐一處理每個 JSON 檔案
    for json_file in json_files:
        # 建立來源檔案的完整路徑
        source_path = os.path.join(QUESTION_JSON_DIR, json_file)
        # 建立目標檔案的完整路徑
        destination_path = os.path.join(QUESTION_JSON_DONE_DIR, json_file)

        # 使用 shutil.move 函數移動檔案
        # 此操作會將檔案從來源路徑移至目標路徑
        try:
            shutil.move(source_path, destination_path)
            logger.info(f"已成功移動檔案: {json_file}")
        except Exception as e:
            # 捕捉可能發生的錯誤並記錄
            logger.error(f"移動檔案 {json_file} 時發生錯誤: {str(e)}")

    logger.info("檔案移動作業完成")


def remove_duplicate_files_from_question_json_all():
    """
    移除 QUESTION_JSON_ALL_DIR 中與已處理檔案重複的檔案

    此 function 負責清理 QUESTION_JSON_ALL_DIR 目錄中與已處理完成的檔案重複的檔案，
    避免資料重複並保持檔案系統的整潔。

    流程：
    1. 獲取已處理完成的 JSON 檔案列表
    2. 檢查這些檔案是否存在於 QUESTION_JSON_ALL_DIR 中
    3. 如果存在，則移除這些重複檔案
    4. 統計並記錄移除的檔案數量
    """
    logger.info("開始執行重複檔案清理作業")

    # 取得已處理完成的檔案目錄路徑
    folder_path = os.path.join(QUESTION_JSON_DONE_DIR)
    logger.info(f"正在檢查已處理目錄: {folder_path}")

    # 使用 list comprehension 取得處理資料夾內所有 JSON 檔案列表
    # 篩選條件為檔名必須以 .json 結尾
    json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    logger.info(f"找到 {len(json_files)} 個已處理的 JSON 檔案")

    # 移除 QUESTION_JSON_ALL_DIR 中相同檔名的檔案
    # 計數器用於統計實際刪除的檔案數量
    deleted_count = 0
    for json_file in json_files:
        # 建立目標檔案的完整路徑
        target_path = os.path.join(QUESTION_JSON_ALL_DIR, json_file)
        # 檢查目標檔案是否存在
        if os.path.exists(target_path):
            try:
                # 如果存在則刪除該檔案
                os.remove(target_path)
                deleted_count += 1
                logger.info(f"已移除重複檔案: {target_path}")
            except Exception as e:
                # 捕捉可能發生的錯誤並記錄
                logger.error(f"移除檔案 {target_path} 時發生錯誤: {str(e)}")

    logger.info(f"重複檔案清理作業完成，共移除 {deleted_count} 個重複檔案")


def update_mongodb():
    """
    更新 MongoDB 資料庫中已處理檔案的狀態標記

    此 function 負責將已處理完成的 JSON 檔案對應的資料庫記錄標記為已解析狀態。
    通過批量更新操作提高效率，避免逐一更新造成的效能問題。

    流程：
    1. 獲取已處理完成的 JSON 檔案列表
    2. 提取檔案名稱作為資料庫中的 id 識別符
    3. 使用批量更新操作將對應記錄的 parsed 欄位設為 true
    4. 記錄更新操作的結果與統計資訊
    """
    logger.info("開始執行 MongoDB 資料庫更新作業")

    # 建立已處理檔案目錄的完整路徑
    folder_path = os.path.join(QUESTION_JSON_DONE_DIR)
    logger.info(f"正在讀取已處理目錄: {folder_path}")

    # 取得處理資料夾內所有 JSON 檔案列表
    json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    logger.info(f"找到 {len(json_files)} 個已處理的 JSON 檔案")

    # 取得所有 JSON 檔案的 id (去除副檔名)
    json_files = [os.path.splitext(f)[0] for f in json_files]
    logger.info(f"準備更新 {len(json_files)} 筆資料庫記錄")

    try:
        # 使用批量更新操作，一次更新所有匹配的資料
        result = collection.update_many(
            {"id": {"$in": json_files}},  # 匹配所有存在於 json_files 中的 id
            {"$set": {"parsed": True}},  # 將 parsed 欄位設為 true
        )

        # 記錄更新結果
        logger.info(
            f"資料庫更新完成: 共匹配 {result.matched_count} 筆記錄，實際更新 {result.modified_count} 筆記錄"
        )
    except Exception as e:
        # 捕捉可能發生的錯誤並記錄
        logger.error(f"更新 MongoDB 時發生錯誤: {str(e)}")

    logger.info("MongoDB 資料庫更新作業結束")


if __name__ == "__main__":
    # 主程式進入點，當此檔案被直接執行時（非被 import）才會執行以下程式碼
    logger.info("開始執行資料庫更新與檔案管理主程序")

    # 步驟 1: 將已完成處理的檔案移至 done 目錄
    # 此 function 負責將處理完畢的檔案從工作目錄移至歸檔目錄，確保工作目錄保持整潔
    logger.info("執行步驟 1: 移動已完成處理的檔案")
    move_completed_files_to_done_dir()

    # 步驟 2: 清理重複檔案
    # 此 function 負責識別並移除 question_json_all 目錄中的重複檔案
    # 避免系統處理重複資料，提高效率並節省儲存空間
    logger.info("執行步驟 2: 清理重複檔案")
    remove_duplicate_files_from_question_json_all()

    # 步驟 3: 更新 MongoDB 資料庫狀態
    # 此 function 將已處理檔案的狀態在資料庫中標記為已解析
    # 確保資料庫狀態與實際檔案處理狀態保持同步
    logger.info("執行步驟 3: 更新 MongoDB 資料庫狀態")
    update_mongodb()

    # 記錄整個流程完成
    logger.info("資料庫更新與檔案管理主程序執行完畢")
