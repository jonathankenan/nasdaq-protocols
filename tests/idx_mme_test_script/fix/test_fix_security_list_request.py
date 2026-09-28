import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Query instrument reference data for a specific symbol via FIX, ##
## instead of checking manually in Nasdaq Core Desktop. ##

LOG_FILE = hlp.setup_logging()


@pytest.mark.asyncio
async def test_fix_security_list_request():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_limit.csv')

    user = credentials[0]
    symbol = orders[0]['Symbol']

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        request = new_security_list_request(symbol)
        logging.info(f"Sending SecurityListRequest, SecurityReqID: {request.SecurityReqID}, symbol: {symbol}")
        fix_session.send_msg(request)

        response = await fix_session.receive_msg()
        logging.info(f"SecurityList received: {response}")

        assert isinstance(response, fix_oe_50.SecurityList), f"Unexpected response type: {response}"

        for security in response.NoRelatedSym:
            logging.info(f"Symbol: {security.Symbol}, SecurityType: {security.SecurityType}")
    finally:
        await fix_session.close()


def new_security_list_request(symbol):
    request: fix_oe_50.SecurityListRequest = fix_oe_50.SecurityListRequest()
    request.SecurityReqID = hlp.generate_ordertoken()
    request.SecurityListRequestType = fix_oe_50.SecurityListRequestType.Symbol
    request.Symbol = symbol
    return request
