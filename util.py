"""
提供處理考試題庫相關的utils

主要功能包括：
1. 圖片處理：合併、轉換和儲存PDF中的圖片
2. 文字處理：處理考試題目和選項的文字內容
3. 資料結構轉換：將處理後的資料轉換為標準格式

compose_images function：將PDF頁面中的分散圖片按照位置合併成完整圖片
extract_text_with_images function：從PDF中提取文字和圖片

"""

import os
import io
from PIL import Image, ImageOps
from pdfplumber import page


def compose_images(
    pieces: list[dict], page: page, pdf_name: str, page_num: int, folder_name: str
) -> list[dict]:

    return_list: list[dict] = []

    # 依x0分組圖片
    grouped_images = {}
    for img in pieces:
        x0 = img["x0"]
        if x0 not in grouped_images:
            grouped_images[x0] = []
        grouped_images[x0].append(img)

    # 建立合併圖片儲存目錄
    os.makedirs("merged_images", exist_ok=True)

    # 遍歷每組圖片進行合併
    for group_idx, (group_key, imgs) in enumerate(grouped_images.items(), 1):
        if not imgs:
            continue

        # 依y0排序圖片（PDF座標y0越大表示越上方<所以需要reverse>）
        sorted_imgs = sorted(imgs, key=lambda x: x["y0"], reverse=True)

        # 提取所有PIL圖片並計算總尺寸
        pil_imgs = []
        total_height = 0
        max_width = 0
        file_format = None
        top = None
        for idx, img in enumerate(sorted_imgs):
            stream = img["stream"].get_data()
            try:
                pil_img = Image.open(io.BytesIO(stream))
            except Image.UnidentifiedImageError:
                print(
                    f"無法識別圖片，跳過此組：頁面 {page_num}, 圖片 group_idx:{group_idx}"
                )
                pil_imgs = []
                break  # 改為break跳出整個圖片組的處理迴圈

            pil_imgs.append(pil_img)
            total_height += pil_img.height
            max_width = max(max_width, pil_img.width)
            if not top:
                top = img["top"]
            if not file_format:
                # 檢測圖片格式
                file_format = detect_image_format(stream)
                # 非指定格式直接跳過
                if not file_format:
                    print(
                        f"跳過非支援格式圖片：頁面 {page_num}, 圖片 group_idx:{group_idx}, idx:{idx}"
                    )
                    break  # 改為break跳出整個圖片組的處理迴圈

        # 如果pil_imgs為空則跳過後續處理
        if not pil_imgs:
            continue

        # 建立空白畫布並合併圖片
        merged_img = Image.new("RGB", (max_width, total_height))
        y_offset = 0
        for pil_img in pil_imgs:
            merged_img.paste(pil_img, (0, y_offset))
            y_offset += pil_img.height

        # 儲存合併後的圖片
        image_filename = (
            f"{pdf_name}_page{page_num}_img{group_idx}.{file_format.lower()}"
        )
        output_path = os.path.join(folder_name, image_filename)
        merged_img.save(output_path, file_format)

        # 計算合併後圖片的實際座標範圍

        x0 = min(img["x0"] for img in sorted_imgs)
        x1 = max(img["x1"] for img in sorted_imgs)
        y0 = min(img["y0"] for img in sorted_imgs)
        y1 = max(img["y1"] for img in sorted_imgs)

        # 根據圖片數量決定bbox取值方式
        if len(sorted_imgs) == 1:
            merged_bbox = [
                sorted_imgs[0]["x0"],
                sorted_imgs[0]["y0"],
                sorted_imgs[0]["x1"],
                sorted_imgs[0]["y1"],
            ]
        else:
            merged_bbox = [x0, y0, x1, y1]

        return_list.append(
            {
                "filename": image_filename,
                "bbox": merged_bbox,
                "top": top,
                "page": page_num,
            }
        )

        print(f"已合併圖片 {group_idx}，儲存至: {output_path}")
        print(f"原始座標範圍: x0={x0:.2f}, y0={y0:.2f}, x1={x1:.2f}, y1={y1:.2f}")

    return return_list


def detect_image_format(image_stream: bytes) -> str:
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
        return None
    else:
        return file_format
