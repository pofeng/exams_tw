import subprocess
import re

# Run pdftotext command
subprocess.run(['pdftotext', 'A1.pdf'])

# Read the text file
with open('A1.txt', 'r') as f:
    text = f.read()

# Find all answer letters
answers = re.findall(r'[ＡＢＣＤ＃]', text)


# Remove the first '#' if it exists
if answers and answers[0] == '＃':
    del answers[0]


# Print the answers
for i, answer in enumerate(answers):
    print(f'{i+1}: {answer}')

# 有多讀入備註後的 ＢＣ 但是先不刪除 , 合併時應該不會輸出
