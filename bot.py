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
        "🤖 Reverse AI فعاله!\n\n"
        "هر چند پیام، یه سؤال تصادفی از یکی از اعضا می‌پرسم "
        "و گاهی هم یه نظرسنجی برای کل گروه می‌سازم."
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

    # Group only
    if chat.type not in ("group", "supergroup"):
        return

    # Ignore bots
    if user is None or user.is_bot:
        return

    # Text only
    if not message.text:
        return

    chat_id = chat.id
    user_id = user.id
    text = message.text.strip()

    ensure_group(chat_id)

    # --------------------------------------------------
    # 1. Check whether this user is answering a question
    # --------------------------------------------------

    pending = get_pending_question(
        chat_id,
        user_id,
    )

    if pending:
        question = pending["question"]

        # Don't count the answer as a new normal message.
        try:
            await message.reply_text(
                "🧠 دارم فکر می‌کنم..."
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
                "❌ یه مشکلی هنگام ارتباط با AI پیش اومد."
            )

        return

    # --------------------------------------------------
    # 2. Make sure user exists
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
    # 3. Count user's message
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
    # 4. Personal question
    # --------------------------------------------------

    if user_count >= user_data["target_count"]:
        try:
            question = await generate_personal_question()

            set_question(
                chat_id,
                user_id,
                question,
            )

            await message.reply_text(
                f"🤔 یه سؤال برای تو:\n\n{question}"
            )

        except Exception:
            logger.exception(
                "Error generating personal question"
            )

            await message.reply_text(
                "❌ نتونستم سؤال بسازم؛ بعداً دوباره امتحان می‌کنم."
            )

        # Don't return here.
        # The group message should still count.

    # --------------------------------------------------
    # 5. Count group messages
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

    # Lock immediately to prevent duplicate polls.
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

        set_poll_active(chat_id, False)


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
        # Close poll and get final results.
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
                "📊 رأی‌گیری تموم شد!\n\n"
                f"🤖 انتخاب من: {ai_option}\n\n"
                f"🧠 دلیل من:\n{reason}"
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


def context_has_job_queue():
    try:
        from telegram.ext import JobQueue

        return JobQueue is not None
    except ImportError:
        return False


if __name__ == "__main__":
    main()
