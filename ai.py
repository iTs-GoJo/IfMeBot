import json
import httpx

from config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_MODEL,
)


async def call_ai(
    messages,
    temperature=0.9,
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


    async with httpx.AsyncClient(
        timeout=60
    ) as client:

        response = await client.post(
            url,
            headers=headers,
            json=payload
        )

        response.raise_for_status()

        data = response.json()


    return (
        data["choices"][0]
        ["message"]
        ["content"]
        .strip()
    )



# ---------------- PERSONAL QUESTION ----------------


async def generate_personal_question():

    messages = [

        {
            "role": "system",
            "content": """
تو یه رفیق خودمونی توی تلگرامی.

هر از گاهی یه سوال جالب، عجیب یا فان از یه نفر بپرس.

قوانین:
- فارسی خودمونی
- کوتاه
- جذاب
- باعث فکر کردن بشه
- رسمی نباشه
- مثل ربات حرف نزن
- اطلاعات شخصی حساس نپرس

فقط خود سوال رو بنویس.
"""
        },

        {
            "role": "user",
            "content":
            "یه سوال رندوم بساز 😂"
        }

    ]


    return await call_ai(
        messages,
        temperature=1.1,
        max_tokens=150
    )



# ---------------- PERSONAL ANSWER ----------------


async def analyze_personal_answer(
    question,
    answer
):

    messages = [

        {
            "role": "system",
            "content": """
تو یه رفیق تلگرامی هستی.

به جواب کاربر نگاه کن و تصور کن خودت جای اون بودی.

بگو:
- اگه جای اون بودی همین انتخاب رو می‌کردی؟
- یا یه انتخاب دیگه؟

لحن:
- خودمونی
- کوتاه
- دوستانه
- کمی فان

مثل:
"من جای تو بودم احتمالاً همینو می‌زدم 😂 چون..."

تحلیل شخصیت نکن.
رسمی حرف نزن.
"""
        },

        {
            "role": "user",
            "content": f"""
سوال:
{question}

جواب:
{answer}
"""
        }

    ]


    return await call_ai(
        messages,
        temperature=0.8,
        max_tokens=250
    )



# ---------------- GROUP POLL ----------------


async def generate_poll():

    messages = [

        {
            "role": "system",
            "content": """
تو یه عضو باحال یه گروه تلگرامی هستی.

یک نظرسنجی جذاب بساز.

موضوع:
تصمیم‌های فرضی، انتخاب‌های سخت، چیزهای فان.

قوانین:
- فارسی خودمونی
- 4 گزینه دقیق
- سوال باعث بحث بشه
- رسمی نباشه

خروجی فقط JSON معتبر باشد:

{
 "question":"",
 "options":[
   "",
   "",
   "",
   ""
 ],
 "ai_choice":0,
 "reason":"",
 "challenge_mode":true
}


توضیح:

ai_choice:
شماره انتخاب خودت از 0 تا 3

reason:
دلیل کوتاه و خودمونی

challenge_mode:
گاهی true و گاهی false.
اگر true باشد بعداً ممکن است با اکثریت مخالفت کنی.
"""
        },


        {
            "role": "user",
            "content":
            "یه نظرسنجی خفن بساز 😂"
        }

    ]


    raw = await call_ai(
        messages,
        temperature=1.2,
        max_tokens=500
    )


    raw = raw.strip()


    if raw.startswith("```"):

        raw = raw.replace(
            "```json",
            ""
        )

        raw = raw.replace(
            "```",
            ""
        )

        raw = raw.strip()



    data = json.loads(raw)


    if len(data["options"]) != 4:
        raise ValueError(
            "Poll must have 4 options"
        )


    if data["ai_choice"] not in range(4):
        raise ValueError(
            "Invalid ai choice"
        )


    return {

        "question":
            data["question"],

        "options":
            data["options"],

        "ai_choice":
            int(data["ai_choice"]),

        "reason":
            data["reason"],

        "challenge_mode":
            bool(
                data.get(
                    "challenge_mode",
                    False
                )
            )
    }



# ---------------- FINAL POLL OPINION ----------------


async def create_final_poll_opinion(
    question,
    options,
    ai_choice,
    result
):

    messages = [

        {
            "role": "system",
            "content": """
تو بعد از یک نظرسنجی گروهی نظر خودت رو می‌گی.

لحن:
- خودمونی
- مثل عضو گروه
- کوتاه
- کمی فان

اگر اکثریت با انتخاب تو بودند:
بگو خوشحالم که هم‌نظر شدیم.

اگر مخالف بودند:
بگو باحال بود ولی من هنوز انتخاب خودم رو ترجیح می‌دم.

در آخر دلیل کوتاه بده.
"""
        },


        {
            "role": "user",
            "content": f"""
سوال:
{question}

گزینه‌ها:
{options}

انتخاب من:
{ai_choice}

نتیجه رای:
{result}
"""
        }

    ]


    return await call_ai(
        messages,
        temperature=0.8,
        max_tokens=250
    )
