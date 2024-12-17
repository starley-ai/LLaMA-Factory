import pandas as pd
import json
from typing import Literal

def build_system_prompt(row):
    advice = row['追加のプロンプト指示']
    if pd.isna(advice):
        advice = ""
    advice_section = f"""

## アドバイス
{advice.replace('\\n', '\n')}""" if advice else ""

    system_prompt = f"""# 指示
{row['AIの名前']}が{row['ユーザーの名前']}と通話をしています。'{row['AIの名前']}のプロフィール' , '{row['ユーザーの名前']}のプロフィール' , '補足情報', '現在の会話' を踏まえて、{row['AIの名前']}の返答を生成してください。

# {row['AIの名前']}のプロフィール:
{row['AIの設定'].replace('\\n', '\n')}

# {row['ユーザーの名前']}のプロフィール:
{row['AIが知っていることやそれまでの会話の要約'].replace('\\n', '\n')}

# 補足情報
## 会話の情報
{row['状況'].replace('\\n', '\n')}{advice_section}

# 注意
出力は必ず{row['AIの名前']}の返答のみであること"""
    return system_prompt

def build_user_and_assistant(row, mode: Literal["sft", "dpo"]):
    ai_name = row['AIの名前']
    user_name = row['ユーザーの名前']

    # 会話履歴をエスケープ済改行コードで分割してパース
    if mode == "sft":
        split_char = "\\n"
    elif mode == "dpo":
        split_char ="\n"
    else:
        raise ValueError(f"Invalid mode: {mode}")

    try:
        messages = row['それまでの会話履歴'].split(split_char)
    except Exception as e:
        print(row['ID'])
        raise e

    all_messages = []
    for i, msg in enumerate(messages):
        if msg.startswith(f"{ai_name}:"):
            all_messages.append({
                "index": i,
                "message": msg.replace(f"{ai_name}:", "").strip(),
                "speaker": "ai"
            })
        elif msg.startswith(f"{user_name}:"):
            all_messages.append({
                "index": i,
                "message": msg.replace(f"{user_name}:", "").strip(),
                "speaker": "user"
            })
        else:
            # (10秒ほどの沈黙）みたいなやつはuserのメッセージとして扱う
            if "沈黙）" in msg or "無音)" in msg:
                all_messages.append({
                    "index": i,
                    "message": msg,
                    "speaker": "user"
                })
            elif mode == "dpo" and "の返答:" in msg:
                # Skip like メイトの返答:
                pass
            else:
                raise ValueError(f"Invalid message format! row num: {row['ID']}, message: {msg}")

    # 返答を最後のメッセージとして追加
    if mode == "sft":
        all_messages.append({
            "index": len(messages),
            "message": row['AIの返答'],
            "speaker": "ai"
        })
        all_messages.sort(key=lambda x: x["index"])

    formatted_messages = []
    for msg in all_messages:
        role = "assistant" if msg["speaker"] == "ai" else "user"
        formatted_messages.append({
            "from": role,
            "value": msg["message"]
        })

    return formatted_messages


def build_sft_conversation(row):
    conversation = {
        "id": row['ID'],
        "conversations": build_user_and_assistant(row, mode="sft"),
        "system": build_system_prompt(row)
    }
    return conversation


def build_dpo_conversation(row):
    conversation = {
        "id": row['ID'],
        "conversations": build_user_and_assistant(row, mode="dpo"),
        "system": build_system_prompt(row),
        "chosen": {
            "from": "assistant",
            "value": row['chosen']
        },
        "rejected": {
            "from": "assistant",
            "value": row['rejected']
        },
    }
    return conversation


def convert_to_sharegpt(mode: Literal["sft", "dpo"]):
    # 各行をShareGPT形式に変換
    if mode == "sft":
        df = pd.read_csv("./scripts/starley/data/train_sft.csv")
        sharegpt_data = []
        for _, row in df.iterrows():
            if row['ID'] == 410:
                continue

            msg = build_sft_conversation(row)
            sharegpt_data.append(msg)
    elif mode == "dpo":
        df = pd.read_csv("./scripts/starley/data/train_dpo.csv")
        sharegpt_data = []
        for _, row in df.iterrows():
            msg = build_dpo_conversation(row)
            sharegpt_data.append(msg)
            # break
    else:
        raise ValueError(f"Invalid mode: {mode}")

    return sharegpt_data


if __name__ == "__main__":
    sft_data = convert_to_sharegpt("sft")
    with open("sft.json", "w", encoding="utf-8") as f:
        json.dump(sft_data, f, indent=4, ensure_ascii=False)

    dpo_data = convert_to_sharegpt("dpo")
    with open("dpo.json", "w", encoding="utf-8") as f:
        json.dump(dpo_data, f, indent=4, ensure_ascii=False)
