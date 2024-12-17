"""
坂田さんが作ったcotomoのDPOデータを convert_to_sharegpt.py が受け付ける形式にパースする
"""

import json
import re
import csv

def parse_prompt(prompt_text):
    # プロンプトの各要素を抽出
    # 最初の改行の次の文字が「次」の場合の特別処理
    first_line = prompt_text.split('\n')[1]
    if first_line.startswith('次'):
        ai_name = re.search(r'会話が行われた状況や(.+?)が', prompt_text).group(1)
        user_name = re.search(rf"{ai_name}が(.+?)に", prompt_text).group(1)
    else:
        ai_name = re.search(r'\n(.+?)が', prompt_text).group(1)
        user_name = re.search(r'が(.+?)と通話', prompt_text).group(1)

    # 状況の抽出
    situation = ""
    if "時刻" in prompt_text:
        situation_match = re.search(r'時刻.*?(?=####|$)', prompt_text, re.DOTALL)
        if situation_match:
            situation = situation_match.group().strip()
            situation = situation.replace("時刻", "- 時刻")

    # AIが知っていることの抽出
    knowledge = ""
    if "知っていること:\n" in prompt_text:
        knowledge_match = re.search(r'知っていること:\n(.*?)(?=####|$)', prompt_text, re.DOTALL)
        if knowledge_match:
            knowledge = knowledge_match.group(1).strip()

    # AI設定の抽出
    settings = ""
    if "の設定:\n" in prompt_text:
        settings_match = re.search(r'の設定:\n(.*?)(?=####|$)', prompt_text, re.DOTALL)
        if settings_match:
            settings = settings_match.group(1).strip()

    # 追加指示の抽出
    advice = ""
    if "アドバイス:\n" in prompt_text:
        advice_match = re.search(r'アドバイス:\n(.*?)(?=####|$)', prompt_text, re.DOTALL)
        if advice_match:
            advice = advice_match.group(1).strip()

    # 会話履歴の抽出
    conversation = ""
    if "#### 会話\n" in prompt_text:
        conversation = prompt_text.split("#### 会話\n")[1].strip()
        if conversation and "返答を生成するときのアドバイス" in conversation:
            advice_line = conversation.split(')')[0]  # 1行目を取得
            advice = advice_line
            conversation = '\n'.join(conversation.split('\n')[1:])  # 2行目以降を会話履歴として保持
        elif conversation and "ニュースについて紹介して、自分の感想を言おう。" in conversation:
            parse_char = ")"
            advice_line = conversation.split(parse_char)[0]  # 1行目を取得
            advice = advice_line
            conversation = '\n'.join(line.lstrip('\n') for line in conversation.split(parse_char)[1:])  # 2行目以降を会話履歴として保持
        elif conversation and "深堀して聞いてみよう" in conversation:
            parse_char = ")"
            advice_line = conversation.split(parse_char)[0]  # 1行目を取得
            advice = advice_line
            conversation = '\n'.join(line.lstrip('\n') for line in conversation.split(parse_char)[1:])  # 2行目以降を会話履歴として保持

    return {
        "AIの名前": ai_name,
        "ユーザーの名前": user_name,
        "状況": situation,
        "AIが知っていることやそれまでの会話の要約": knowledge,
        "AIの設定": settings,
        "追加のプロンプト指示": advice,
        "それまでの会話履歴": conversation
    }

def load_and_parse_jsonl(file_path):
    parsed_data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            data = json.loads(line)
            prompt = data['prompt']
            parsed = parse_prompt(prompt)
            parsed['ID'] = i + 1
            parsed_data.append(parsed)
            parsed['chosen'] = data['chosen']
            parsed['rejected'] = data['rejected']
            # break
    return parsed_data


if __name__ == "__main__":
    parsed_data = load_and_parse_jsonl("sakata_dpo.jsonl")

    # CSVファイルに書き込み
    with open('train_dpo.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'AIの名前', 'ユーザーの名前', '状況', 'AIが知っていることやそれまでの会話の要約', 'AIの設定', '追加のプロンプト指示', 'それまでの会話履歴', 'chosen', 'rejected'])
        writer.writeheader()
        for data in parsed_data:
            writer.writerow(data)
