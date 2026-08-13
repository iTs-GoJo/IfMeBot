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
)

from config import (
    TELEGRAM_BOT_TOKEN,
    PERSONAL_MIN_MESSAGES,
    PERSONAL_MAX_MESSAGES,
    GROUP_POLL_MESSAGES,
    POLL_DURATION_SECONDS,
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
    increment_group_messages,
    get_group,
    reset_group_messages,
    set_poll_active,
    save_poll,
    get_poll,
    delete_poll,
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
        "من یه باتم که هر از گاهی یه سؤال عجیب‌غریب "
        "می‌پرسم و بعد می‌گم اگه جای شما بودم چی کار می‌کردم.\n\n"
        "حواستون باشه ممکنه یهو وسط چت سر و کله‌م پیدا شه 👀"
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

    # فقط گروه و سوپرگروه
    if chat.type not in ("group", "supergroup"):
        return

    # پیام بات‌ها شمرده نشود
    if user is None or user.is_bot:
        return

    # فعلاً فقط پیام متنی
    if not message.text:
        return

    chat_id = chat.id
    user_id = user.id
    text = message.text.strip()

    ensure_group(chat_id)

    # --------------------------------------------------
    # پاسخ به سؤال شخصی
    # --------------------------------------------------

    pending = get_pending_question(
        chat_id,
        user_id,
    )

    if pending:
        reply = message.reply_to_message

        # فقط اگر کاربر واقعاً Reply کرده باشد
        # و Reply دقیقاً به سؤال بات باشد
        if (
            reply
            and reply.from_user
            and reply.from_user.is_bot
            and reply.message_id == pending["question_message_id"]
        ):
            question = pending["question"]

            try:
                await message.reply_text(
                    "🧠 صبر کن ببینم چی می‌گم 😂"
                )

                answer = await analyze_personal_answer(
                    question,
                    text,
                )

                await message.reply_text(
                    f"🤖 {answer}"
                )

                new_target = random.randint(
                    PERSONAL_MIN_MESSAGES,
                    PERSONAL_MAX_MESSAGES,
                )

                finish_question(
                    chat_id,
                    user_id,
                    new_target,
                )

            except Exception:
                logger.exception(
                    "Error while analyzing answer"
                )

                await message.reply_text(
                    "😂 یه مشکلی پیش اومد، جوابم نرسید."
                )

            return

        # اگر Reply نکرده، پیام عادی حساب می‌شود.
        # یعنی سؤال همچنان منتظر پاسخ است.

    # --------------------------------------------------
    # ساخت کاربر
    # --------------------------------------------------

    user_data = get_user(
        chat_id,
        user_id,
    )

    if user_data is None:
        target = random.randint(
            PERSONAL_MIN_MESSAGES,
            PERSONAL_MAX_MESSAGES,
        )

        create_user(
            chat_id,
            user_id,
            target,
        )

    # --------------------------------------------------
    # شمارش پیام کاربر
    # --------------------------------------------------

    user_count = increment_user_messages(
        chat_id,
        user_id,
    )

    user_data = get_user(
        chat_id,
        user_id,
    )

    # --------------------------------------------------
    # سؤال شخصی
    # --------------------------------------------------

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
                "Error generating personal question"
            )

            await message.reply_text(
                "😂 مغزم هنگ کرد، فعلاً سؤال ندارم."
            )

    # --------------------------------------------------
    # شمارش پیام‌های کل گروه
    # --------------------------------------------------

    group_count = increment_group_messages(
        chat_id
    )

    group_data = get_group(chat_id)

    if (
        group_count >= GROUP_POLL_MESSAGES
        and not group_data["poll_active"]
    ):
        await create_group_poll(
            update,
            context,
        )


async def create_group_poll(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    chat_id = update.effective_chat.id

    # قفل فوری برای جلوگیری از Poll تکراری
    set_poll_active(chat_id, True)

    try:
        poll = await generate_poll()

        question = poll["question"]
        options = poll["options"]
        ai_choice = poll["ai_choice"]
        reason = poll["reason"]

        sent = await context.bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=False,
            allows_multiple_answers=False,
        )

        options_text = "\n".join(
            f"{i}. {option}"
            for i, option in enumerate(options)
        )

        save_poll(
            chat_id=chat_id,
            message_id=sent.message_id,
            question=question,
            options=options_text,
            ai_choice=ai_choice,
            reason=reason,
        )

        reset_group_messages(chat_id)

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
            "Error creating group poll"
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
        set_poll_active(chat_id, False)
        return

    try:
        result = await context.bot.stop_poll(
            chat_id=chat_id,
            message_id=message_id,
        )

        ai_choice = poll_data["ai_choice"]
        reason = poll_data["reason"]

        ai_option = result.options[ai_choice].text

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "📊 خب، رأی‌گیری تموم شد 😂\n\n"
                f"🤖 من: {ai_option}\n\n"
                f"💭 دلیلش:\n{reason}"
            ),
        )

    except Exception:
        logger.exception(
            "Error finishing poll"
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
        "Reverse AI started..."
    )

    application.run_polling()


if __name__ == "__main__":
    main()
