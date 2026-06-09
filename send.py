import asyncio

from db import (
    get_all_users,
    get_setting,
    add_broadcast,
    add_admin_log
)


async def broadcast_forward(
    bot,
    admin_id,
    source_chat,
    source_message
):
    users = get_all_users()

    delay = float(
        get_setting(
            "broadcast_delay"
        ) or 0.5
    )

    success = 0
    failed = 0

    for user in users:

        user_id = user[0]

        try:

            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=source_chat,
                message_id=source_message
            )

            success += 1

        except Exception:

            failed += 1

        await asyncio.sleep(delay)

    add_broadcast(
        admin_id,
        success,
        failed
    )

    add_admin_log(
        admin_id,
        "broadcast",
        f"{success}/{failed}"
    )

    return {
        "success": success,
        "failed": failed,
        "total": success + failed
    }