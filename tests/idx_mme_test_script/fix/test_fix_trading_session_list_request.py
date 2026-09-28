import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Query the current trading session state directly via FIX, ##
## instead of checking manually in Nasdaq Core Desktop. ##

LOG_FILE = hlp.setup_logging()


@pytest.mark.asyncio
async def test_fix_trading_session_list_request():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    user = credentials[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        request = new_trading_session_list_request()
        logging.info(f"Sending TradingSessionListRequest, TradSesReqID: {request.TradSesReqID}")
        fix_session.send_msg(request)

        response = await fix_session.receive_msg()
        logging.info(f"TradingSessionList received: {response}")

        assert isinstance(response, fix_oe_50.TradingSessionList), f"Unexpected response type: {response}"

        for session in response.NoTradingSessions:
            logging.info(
                f"TradingSessionID: {session.TradingSessionID}, "
                f"TradSesStatus: {session.TradSesStatus}"
            )
    finally:
        await fix_session.close()


def new_trading_session_list_request():
    request: fix_oe_50.TradingSessionListRequest = fix_oe_50.TradingSessionListRequest()
    request.TradSesReqID = hlp.generate_ordertoken()
    request.SubscriptionRequestType = fix_oe_50.SubscriptionRequestType.Snapshot
    return request
