# exams_tw
台灣國家考試題庫

考選部 考畢試題查詢平臺 https://wwwq.moex.gov.tw/exam/wFrmExamQandASearch.aspx

考選部 資料開放專區 https://wwwc.moex.gov.tw/main/content/SubMenu.aspx?menu_id=2251

url.csv 網址對照表 (連結網址開放資料): https://wwwc.moex.gov.tw/main/Exam/wHandExamQandA_CSV.ashx

dl.py + url.csv 可以下載所有的考卷, 抓完有 89484 個 pdf , 未壓縮 13.1 G , 89484 個 pdf 

在 Gemini Pro 2.5 ( 在 google ai studio )
可以直接上傳題目跟答案 pdf , 然後請他組成 MMLU json 
也可以直接請他考試後對答案
https://aistudio.google.com/app/prompts/1MT6U__71rQGIb7h3QA2UNvxtQ1KAnq9B

----

目前有看起來選擇題有兩種格式, 先選簡單的, 範例為 Q1.pdf 與 A1.pdf , 對應到 Q1.py A1.py , 有呼叫 pdftotext 需要安裝 poppler-utils

希望下一步能組成 MMLU-example.json 的格式, 然後用 lm-evaluation-harness 去評 perplexity R1 1776

----

## Ken的說明
1. url.csv中有60316筆資料，但是我將其轉錄成json後，fse_all.json只有60251筆記錄


### 檔案/資料夾說明
1. question_bank - 裡頭是所有的題庫、答案pdf檔
2. question_json_all - 每一份考卷與對應的答案都被我整理了一張一張的json
3. fest_all.json - 這個檔案是所有json的集合
4. question_json - 這是處理中的folder。先在csv或mongodb上決定好要處理的檔案們，將這些實體json由*question_json_all* copy至此。再這裡測試、實做。
5. question_images - 有圖片的考卷，該圖片檔會暫時被放置於此。與前項*question_json*的處理方式一樣，完成後應將question_images內所有圖片檔copy至*question_images_done*
6. question_json_done - 處理完成的json就放置於此
7. question_images_done - 處理完成的images
8. exam_schema.json - 題庫json的schema
要注意的是，question_json_all的內容應該與question_json_done的內容互斥，一個json file只能存在於一個folder中。尚未處理的置於question_json_all，已處理完成的置於question_json_done。


2.  
圖片處理有用到wand
```python
pip install wand
# macOS用Homebrew安裝imagemagick
brew install imagemagick
```

### .py的處理範圍
process_exam_type01.py
1. fse00000001.json ~ fse00000065.json
2. fse00000066.json ~ fse00000121.json


<pre>
著作權法第九條
1. 下列各款不得為著作權之標的︰
   一、憲法、法律、命令或公文。
   二、中央或地方機關就前款著作作成之翻譯物或編輯物。
   三、標語及通用之符號、名詞、公式、數表、表格、簿冊或時曆。
   四、單純為傳達事實之新聞報導所作成之語文著作。
   五、依法令舉行之各類考試試題及其備用試題。
2. 前項第一款所稱公文，包括公務員於職務上草擬之文告、講稿、新聞稿及其他文書
</pre>


