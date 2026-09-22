import asyncio
import logging
import pytest

from tests.idx_mme_helper import utils as hlp

## Test case scenario: Max connection - only 1 active FIX session per account (rule documented for OUCH, spec 3.3) ##

LOG_FILE = hlp.setup_logging()

FIX_HOST = '172.18.2.132'
FIX_PORT = '8200'

@pytest.mark.asyncio
async def test_multi_login_fix():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    user = credentials[0]

    session1 = await hlp.loginFIXFromFile(
        FIX_HOST, FIX_PORT, user['username'], user['password'], user['sender_comp_id']
    )
    assert session1, "First login failed, cannot test max connection behavior."
    logging.info(f"Session 1 established for {user['username']}")

    try:
        # Give session1 a brief moment to fully settle before the 2nd logon.
        await asyncio.sleep(1)

        session2 = await hlp.loginFIXFromFile(
            FIX_HOST, FIX_PORT, user['username'], user['password'], user['sender_comp_id']
        )
        assert session2, "Second login failed -- expected it to succeed and kick out session 1."
        logging.info(f"Session 2 established for {user['username']}")

        try:
            # Give the server a moment to close session1 after session2 logs on.
            await asyncio.sleep(1)

            logging.info(f"Session 1 closed: {session1.is_closed()}")
            assert session1.is_closed(), \
                "Session 1 is still open -- expected it to be force-closed when session 2 logged on."
            logging.info("Max connection behavior confirmed: session 1 was closed by the system.")
        finally:
            if not session2.is_closed():
                await session2.close()
    finally:
        if not session1.is_closed():
            await session1.close()
