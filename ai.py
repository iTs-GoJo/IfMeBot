import json

import httpx

from config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_MODEL,
)


async def call_ai(
    messages,
    temperature=0.8,
    max_tokens=500
):
    url = f"{AI_BASE_URL.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def generate_personal_question():
    messages = [
        {
            "role": "system",
            "content": (
                "You create short, interesting hypothetical "
                "decision questions for a Telegram group. "
                "The question must have a clear choice and "
                "should make the user think. "
                "Do not ask about sensitive personal information. "
                "Do not mention the user or previous messages. "
                "Return ONLY the question in Persian."
            ),
        },
        {
            "role": "user",
            "content": (
                "Create one completely random and interesting "
                "decision question."
            ),
        },
    ]

    return await call_ai(
        messages,
        temperature=1.1,
        max_tokens=150,
    )


async def analyze_personal_answer(
    question: str,
    answer: str
):
    messages = [
        {
            "role": "system",
            "content": (
                "You are answering a hypothetical decision question. "
                "Pretend you are in exactly the same situation. "
                "Compare your own hypothetical choice with the user's "
                "choice. Say whether you would probably choose the "
                "same thing or something else, and briefly explain why. "
                "Respond naturally in Persian. "
                "Do not analyze the user's personality. "
                "Do not mention previous messages."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"User's answer:\n{answer}"
            ),
        },
    ]

    return await call_ai(
        messages,
        temperature=0.8,
        max_tokens=250,
    )


async def generate_poll():
    messages = [
        {
            "role": "system",
            "content": (
                "Create an interesting random hypothetical decision "
                "question for a Telegram poll.\n\n"
                "Return ONLY valid JSON with exactly these fields:\n"
                "{\n"
                '  "question": "string",\n'
                '  "options": ["string", "string", "string", "string"],\n'
                '  "ai_choice": 0,\n'
                '  "reason": "string"\n'
                "}\n\n"
                "Rules:\n"
                "- Persian language.\n"
                "- Exactly 4 options.\n"
                "- ai_choice must be 0, 1, 2, or 3.\n"
                "- reason must briefly explain the AI's choice.\n"
                "- The question must not require personal information.\n"
                "- Make the question fun and debatable.\n"
                "- Do not use previous conversation context."
            ),
        },
        {
            "role": "user",
            "content": "Create one completely random poll.",
        },
    ]

    raw = await call_ai(
        messages,
        temperature=1.1,
        max_tokens=500,
    )

    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1)
        raw = raw.replace("```", "", 1)
        raw = raw.strip()

    data = json.loads(raw)

    question = data["question"]
    options = data["options"]
    ai_choice = int(data["ai_choice"])
    reason = data["reason"]

    if not isinstance(options, list):
        raise ValueError("AI returned invalid options")

    if len(options) != 4:
        raise ValueError("AI must return exactly 4 options")

    if ai_choice not in range(4):
        raise ValueError("Invalid AI choice")

    return {
        "question": question,
        "options": options,
        "ai_choice": ai_choice,
        "reason": reason,
    }
