import logging
import random

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai import (
    generate_personal_question,
    analyze_personal_answer,
    generate_poll,
    create_final_poll_opinion,
)

from levels import (
    get_level,
    get_poll_limit,
    level_up_message,
    get_next_level_xp,
)

from config import (
    TELEGRAM_BOT_TOKEN,
    PERSONAL_MIN_MESSAGES,
    PERSONAL_MAX_MESSAGES,
    POLL_DURATION_SECONDS,
    BOT_CREATOR_ID,
)

from database import (
    init_db,
    ensure_group,
    get_user,
    create_user,
    increment_user_messages,
    set_question,
    get_pending_question,
    finish_question,

    add_group_message,
    get_group,
    update_level,

    reset_group_messages,
    set_poll_active,

    save_poll,
    get_poll,
    delete_poll,

    # group settings helpers
    set_bot_active,
    set_personal_questions_enabled,
    set_polls_enabled,
    get_group_settings,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_chat.type not in (
        "group",
        "supergroup",
    ):
        return


    await update.message.reply_text(
        "😂 سلام بچه‌ها!\n\n"
        "من Reverse AI هستم.\n"
        "گاهی وسط چت یه سؤال عجیب می‌پرسم "
        "و بعد می‌گم اگه جای شما بودم چی انتخاب می‌کردم 😈\n\n"
        "حواستون باشه ممکنه یهو ظاهر شم 👀"
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if not message:
        return

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in (
        "group",
        "supergroup",
    ):
        return

    if user is None or user.is_bot:
        return

    if not message.text:
        return

    chat_id = chat.id
    user_id = user.id
    text = message.text.strip()

    ensure_group(chat_id)

    # Respect per-group bot_active setting
    settings = get_group_settings(chat_id)
    if not settings.get("bot_active", True):
        # Bot is disabled in this group
        return

    # -----------------------------
    # پاسخ به سوال شخصی
    # -----------------------------

    pending = get_pending_question(
        chat_id,
        user_id,
    )

    if pending:

        reply = message.reply_to_message

        if (
            reply
            and reply.from_user
            and reply.from_user.is_bot
            and reply.message_id == pending["question_message_id"]
        ):

            try:

                await message.reply_text(
                    "🧠 دارم فکر می‌کنم 😂"
                )

                answer = await analyze_personal_answer(
                    pending["question"],
                    text,
                )

                await message.reply_text(
                    f"🤖 {answer}"
                )

                finish_question(
                    chat_id,
                    user_id,
                    random.randint(
                        PERSONAL_MIN_MESSAGES,
                        PERSONAL_MAX_MESSAGES,
                    ),
                )

            except Exception:

                logger.exception(
                    "Personal answer error"
                )

                await message.reply_text(
                    "😂 مغزم هنگ کرد، دوباره امتحان کن."
                )

            return

    # -----------------------------
    # ساخت کاربر
    # -----------------------------

    user_data = get_user(
        chat_id,
        user_id,
    )

    if user_data is None:

        create_user(
            chat_id,
            user_id,
            random.randint(
                PERSONAL_MIN_MESSAGES,
                PERSONAL_MAX_MESSAGES,
            ),
        )

    user_count = increment_user_messages(
        chat_id,
        user_id,
    )

    user_data = get_user(
        chat_id,
        user_id,
    )

    # -----------------------------
    # سوال شخصی
    # -----------------------------

    if settings.get("personal_questions_enabled", True):
        if (
            user_count >= user_data["target_count"]
            and not user_data["waiting_answer"]
        ):

            try:

                question = await generate_personal_question()

                sent = await message.reply_text(
                    f"🤔 یه سؤال برات:\n\n{question}"
                )

                set_question(
                    chat_id,
                    user_id,
                    question,
                    sent.message_id,
                )

            except Exception:

                logger.exception(
                    "Question generation error"
                )

    # -----------------------------
    # XP و Level گروه
    # -----------------------------

    old_group = get_group(chat_id)

    old_level = old_group["level"]

    group_data = add_group_message(
        chat_id
    )

    new_level = get_level(
        group_data["xp"]
    )

    if new_level > old_level:

        update_level(
            chat_id,
            new_level,
        )

        level_message = level_up_message(
            old_level,
            new_level,
        )

        if level_message:

            await message.reply_text(
                level_message
            )

    poll_limit = get_poll_limit(
        new_level
    )

    if (
        group_data["message_count"] >= poll_limit
        and not group_data["poll_active"]
        and settings.get("polls_enabled", True)
    ):

        # call the top-level create_group_poll
        await create_group_poll(
            update,
            context,
        )


async def create_group_poll(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    set_poll_active(
        chat_id,
        True,
    )

    try:

        poll = await generate_poll()

        question = poll["question"]
        options = poll["options"]
        ai_choice = poll["ai_choice"]
        reason = poll["reason"]
        challenge_mode = poll["challenge_mode"]

        sent = await context.bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=False,
            allows_multiple_answers=False,
        )

        options_text = "\n".join(
            options
        )

        save_poll(
            chat_id=chat_id,
            message_id=sent.message_id,
            question=question,
            options=options_text,
            ai_choice=ai_choice,
            reason=reason,
            challenge_mode=int(
                challenge_mode
            ),
        )

        reset_group_messages(
            chat_id
        )

        context.job_queue.run_once(
            finish_poll,
            when=POLL_DURATION_SECONDS,
            data={
                "chat_id": chat_id,
                "message_id": sent.message_id,
            },
            name=f"poll_{chat_id}_{sent.message_id}",
        )

    except Exception:

        logger.exception(
            "Create poll error"
        )

        set_poll_active(
            chat_id,
            False,
        )


async def finish_poll(
    context: ContextTypes.DEFAULT_TYPE,
):

    data = context.job.data

    chat_id = data["chat_id"]
    message_id = data["message_id"]

    poll_data = get_poll(
        chat_id,
        message_id,
    )

    if poll_data is None:

        set_poll_active(
            chat_id,
            False,
        )

        return

    try:

        result = await context.bot.stop_poll(
            chat_id=chat_id,
            message_id=message_id,
        )

        ai_choice = poll_data["ai_choice"]

        ai_option = (
            result.options[ai_choice].text
        )

        result_text = "\n".join(
            f"{option.text}: {option.voter_count} رای"
            for option in result.options
        )

        try:

            opinion = await create_final_poll_opinion(
                poll_data["question"],
                poll_data["options"].split("\n"),
                ai_option,
                result_text,
            )

        except Exception:

            logger.exception(
                "AI opinion error"
            )

            opinion = (
                f"من گزینه {ai_option} رو انتخاب می‌کردم 😂"
            )

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "📊 رأی‌گیری تموم شد 😂\n\n"
                f"{result_text}\n\n"
                f"🤖 نظر من:\n{opinion}"
            ),
        )

    except Exception:

        logger.exception(
            "Finish poll error"
        )

    finally:

        delete_poll(
            chat_id,
            message_id,
        )

        set_poll_active(
            chat_id,
            False,
        )


async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    settings = get_group_settings(chat.id)
    level = settings.get("level", 1)
    xp = settings.get("xp", 0)
    next_xp = get_next_level_xp(level)

    if next_xp is None:
        text = f"گروه Level {level} (حداکثر)\nXP: {xp}"
    else:
        text = f"گروه Level {level}\nXP: {xp}\nتا Level {level+1}: {next_xp - xp} XP"

    await update.message.reply_text(text)


async def _user_is_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        logger.exception("Failed to check admin status")
        return False


async def set_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        return

    if user.id != BOT_CREATOR_ID:
        await update.message.reply_text("❌ فقط سازندهٔ ربات می‌تواند این دستور را اجرا کند.")
        return

    arg = (context.args[0].lower() if context.args else "")
    if arg not in ("on", "off"):
        await update.message.reply_text("استفاده: /set_bot on|off")
        return

    set_bot_active(chat.id, arg == "on")
    await update.message.reply_text(f"✅ وضعیت ربات در این گروه: {arg}")


async def set_personal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        return

    is_admin = await _user_is_admin(chat.id, user.id, context)
    if not is_admin:
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند این دستور را اجرا کنند.")
        return

    arg = (context.args[0].lower() if context.args else "")
    if arg not in ("on", "off"):
        await update.message.reply_text("استفاده: /set_personal on|off")
        return

    set_personal_questions_enabled(chat.id, arg == "on")
    await update.message.reply_text(f"✅ سوال‌های شخصی برای این گروه: {arg}")


async def set_polls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        return

    is_admin = await _user_is_admin(chat.id, user.id, context)
    if not is_admin:
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند این دستور را اجرا کنند.")
        return

    arg = (context.args[0].lower() if context.args else "")
    if arg not in ("on", "off"):
        await update.message.reply_text("استفاده: /set_polls on|off")
        return

    set_polls_enabled(chat.id, arg == "on")
    await update.message.reply_text(f"✅ نظرسنجی‌ها برای این گروه: {arg}")


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.exception(
        "Unhandled exception:",
        exc_info=context.error,
    )



def context_has_job_queue():

    try:

        from telegram.ext import JobQueue

        return JobQueue is not None

    except ImportError:

        return False


def main():

    if not TELEGRAM_BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set"
        )

    if not context_has_job_queue():

        raise RuntimeError(
            "Install python-telegram-bot[job-queue]"
        )

    init_db()

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # new command handlers
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("set_bot", set_bot_command))
    application.add_handler(CommandHandler("set_personal", set_personal_command))
    application.add_handler(CommandHandler("set_polls", set_polls_command))

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Reverse AI v2 started..."
    )

    application.run_polling()


if __name__ == "__main__":

    main()
