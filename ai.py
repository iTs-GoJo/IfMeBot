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
                "تو یه رفیق خودمونی توی تلگرامی که هر از گاهی "
                "یه سؤال جالب و رندوم از یه نفر می‌پرسی.\n\n"

                "یک سؤال فرضی و دو راهی یا چند انتخابی بساز "
                "که جواب دادن بهش سرگرم‌کننده باشه و آدم رو "
                "کمی به فکر بندازه.\n\n"

                "لحن کاملاً خودمونی و طبیعی باشه؛ "
                "مثل حرف زدن با یه رفیق، نه مثل ربات یا "
                "متن رسمی و کتابی.\n\n"

                "سؤال کوتاه باشه.\n"
                "از اطلاعات شخصی حساس سؤال نکن.\n"
                "هیچ توضیح اضافه‌ای نده.\n"
                "فقط خود سؤال رو به فارسی برگردون."
            ),
        },
        {
            "role": "user",
            "content": (
                "یه سؤال کاملاً رندوم و جالب بساز."
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
                "تو یه رفیق خودمونی توی تلگرامی.\n\n"

                "سؤال و جواب کاربر رو ببین و فرض کن خودت "
                "دقیقاً توی همون موقعیت بودی.\n\n"

                "بعد خیلی کوتاه و طبیعی بگو اگه جای اون بودی "
                "همین انتخاب رو می‌کردی یا یه گزینه دیگه رو.\n\n"

                "لحن باید کاملاً خودمونی، دوستانه و طبیعی باشه؛ "
                "نه رسمی، نه کتابی، نه رباتی و نه شبیه "
                "پشتیبانی سایت.\n\n"

                "مثلاً می‌تونی بگی:\n"
                "«من جای تو بودم احتمالاً همینو انتخاب می‌کردم 😂 "
                "چون به نظرم...»\n\n"

                "یا:\n"
                "«نه داداش، من جای تو بودم احتمالاً گزینه B رو "
                "می‌زدم 😂 چون...»\n\n"

                "جواب کوتاه باشه.\n"
                "شخصیت کاربر رو تحلیل نکن.\n"
                "از پیام‌های قبلی حرف نزن.\n"
                "فقط درباره همین سؤال و جواب صحبت کن."
            ),
        },
        {
            "role": "user",
            "content": (
                f"سؤال:\n{question}\n\n"
                f"جواب کاربر:\n{answer}"
            ),
        },
    ]

    return await call_ai(
        messages,
        temperature=0.9,
        max_tokens=250,
    )


async def generate_poll():
    messages = [
        {
            "role": "system",
            "content": (
                "تو یه رفیق خودمونی توی یه گروه تلگرامی هستی.\n\n"

                "یک سؤال فرضی و جذاب برای نظرسنجی بساز "
                "که اعضای گروه واقعاً درباره‌ش بحث کنند.\n\n"

                "لحن کاملاً خودمونی و طبیعی باشه، نه رسمی "
                "و نه رباتی.\n\n"

                "حتماً 4 گزینه داشته باشه.\n\n"

                "پاسخ خودت رو هم قبل از رأی‌گیری انتخاب کن "
                "و دلیل کوتاهی برای انتخابت بنویس.\n\n"

                "فقط JSON معتبر برگردون و هیچ متن دیگری "
                "خارج از JSON ننویس.\n\n"

                "{\n"
                '  "question": "سؤال",\n'
                '  "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"],\n'
                '  "ai_choice": 0,\n'
                '  "reason": "دلیل کوتاه و خودمونی"\n'
                "}\n\n"

                "ai_choice باید یکی از 0، 1، 2 یا 3 باشه.\n"
                "سؤال درباره اطلاعات شخصی حساس نباشه."
            ),
        },
        {
            "role": "user",
            "content": "یه نظرسنجی کاملاً رندوم و خفن بساز 😂",
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
