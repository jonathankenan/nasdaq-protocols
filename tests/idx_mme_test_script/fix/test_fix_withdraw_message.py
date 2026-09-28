import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper.state import load_state

## Test case scenario: Withdraw (cancel) an existing order, based on spec section 2.4/2.5 ##
## Requires an order already placed by test_fix_send_order_limit.py in a separate run. ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_fix_withdraw_message():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')

    user = credentials[0]

    try:
        existing_order = load_state('order_limit')
    except FileNotFoundError:
        assert False, "No existing order found. Run test_fix_send_order_limit.py first."

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        # Withdraw (cancel) the order placed earlier by test_fix_send_order_limit.py.
        cancel_request = new_cancel_request(
            orig_cl_ord_id=existing_order['ClOrdID'],
            symbol=existing_order['Symbol'],
            side=existing_order['Side'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending withdraw request for OrigClOrdID: {existing_order['ClOrdID']}")
        fix_session.send_msg(cancel_request)

        cancel_response = await fix_session.receive_msg()
        logging.info(f"Withdraw response: {cancel_response}")

        if isinstance(cancel_response, fix_oe_50.OrderCancelReject):
            assert False, f"Withdraw rejected: {cancel_response.RejectText}"

        assert cancel_response.OrdStatus == fix_oe_50.OrdStatus.Canceled, \
            f"Unexpected status after withdraw: {cancel_response}"
        logging.info(f"Order {existing_order['ClOrdID']} successfully withdrawn.")
    finally:
        await fix_session.close()


def new_cancel_request(orig_cl_ord_id, symbol, side, username, sender_comp_id):
    # Parties here only accepts 2 or 4 entries (unlike NewOrderSingle's 2..5), so CustomerAccount(24) is left out.
    cancel_request: fix_oe_50.OrderCancelRequest = fix_oe_50.OrderCancelRequest()
    cancel_request.OrigClOrdID = orig_cl_ord_id
    cancel_request.ClOrdID = hlp.generate_ordertoken()
    cancel_request.Symbol = symbol
    cancel_request.Side = fix_oe_50.Side.Buy if side == 'B' else fix_oe_50.Side.Sell
    cancel_request.TransactTime = hlp.get_time()

    cancel_request.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
    ]
    return cancel_request
