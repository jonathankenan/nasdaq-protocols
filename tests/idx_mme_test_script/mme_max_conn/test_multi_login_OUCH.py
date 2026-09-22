import asyncio
import logging
import pytest

from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper import ouch_utils as ouch_hlp

## Test case scenario: Max connection - only 1 active OUCH session per account, based on spec 3.3 Fault Redundancy ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_multi_login_ouch():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit_ouch.csv')
    user = credentials[0]

    session1 = await ouch_hlp.loginOUCH(
        ouch_hlp.OUCH_HOST, ouch_hlp.OUCH_PORT, user['username'], user['password']
    )
    assert session1, "First login failed, cannot test max connection behavior."
    logging.info(f"Session 1 established for {user['username']}")

    try:
        await asyncio.sleep(1)

        session2 = await ouch_hlp.loginOUCH(
            ouch_hlp.OUCH_HOST, ouch_hlp.OUCH_PORT, user['username'], user['password']
        )
        assert session2, "Second login failed -- expected it to succeed and kick out session 1."
        logging.info(f"Session 2 established for {user['username']}")

        try:
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
