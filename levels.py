LEVELS = {
    1: 0,
    2: 100,
    3: 300,
    4: 700,
    5: 1200,
    6: 1600,
    7: 2000,
    8: 2500,
    9: 3200,
    10: 4500,
}


def get_level(xp: int) -> int:
    level = 1

    for lvl, needed_xp in LEVELS.items():
        if xp >= needed_xp:
            level = lvl

    return level


def get_next_level_xp(level: int):
    return LEVELS.get(
        level + 1,
        None
    )


def get_poll_limit(level: int) -> int:
    limits = {
        1: 50,
        2: 45,
        3: 40,
        4: 35,
        5: 30,
        6: 25,
        7: 25,
        8: 20,
        9: 20,
        10: 15,
    }

    return limits.get(
        level,
        50
    )


def level_up_message(
    old_level: int,
    new_level: int
):
    if new_level <= old_level:
        return None

    emojis = {
        2: "🥈",
        3: "🥇",
        4: "🔥",
        5: "⚡",
        6: "💎",
        7: "🚀",
        8: "👑",
        9: "🌟",
        10: "🏆",
    }

    emoji = emojis.get(
        new_level,
        "🔥"
    )

    return (
        f"🎉 گروه رفت Level {new_level} {emoji}\n\n"
        "از این به بعد:\n"
        f"• سوال‌ها هر {get_poll_limit(new_level)} پیام ساخته میشن\n"
        "• چالش‌ها سخت‌تر میشن 😈"
  )
