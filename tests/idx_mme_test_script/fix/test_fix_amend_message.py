import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper.state import load_state

## Test case scenario: Amend (cancel/replace) an existing order, based on spec section 2.3 ##
## Requires an order already placed by test_fix_send_order_limit.py in a separate run. ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_fix_amend_message():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    amended_orders = hlp.load_orders('tests/idx_mme_data/data_amend_order_limit.csv')

    user = credentials[0]
    amend_order_data = amended_orders[0]

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
        # Amend the order placed earlier by test_fix_send_order_limit.py.
        # New price/qty are taken from data_amend_order_limit.csv.
        amend_request = new_amend_request(
            orig_cl_ord_id=existing_order['ClOrdID'],
            symbol=amend_order_data['Symbol'],
            side=amend_order_data['Side'],
            qty=amend_order_data['OrderQty'],
            price=amend_order_data['Price'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending amend request for OrigClOrdID: {existing_order['ClOrdID']}, "
                     f"new price: {amend_order_data['Price']}")
        fix_session.send_msg(amend_request)

        amend_response = await fix_session.receive_msg()
        logging.info(f"Amend response: {amend_response}")

        if isinstance(amend_response, fix_oe_50.OrderCancelReject):
            assert False, f"Amend rejected: {amend_response.RejectText}"

        assert amend_response.ExecType == fix_oe_50.ExecType.Replaced, \
            f"Unexpected ExecType after amend: {amend_response}"
        logging.info(f"Order {existing_order['ClOrdID']} successfully amended, "
                     f"new ClOrdID: {amend_request.ClOrdID}")
    finally:
        await fix_session.close()


def new_amend_request(orig_cl_ord_id, symbol, side, qty, price, username, sender_comp_id):
    # Fields marked "not allowed to change but required" must be re-sent with their original value.
    amend_request: fix_oe_50.OrderCancelReplaceRequest = fix_oe_50.OrderCancelReplaceRequest()
    amend_request.OrigClOrdID = orig_cl_ord_id
    amend_request.ClOrdID = hlp.generate_ordertoken()
    amend_request.Symbol = symbol
    amend_request.Side = fix_oe_50.Side.Buy if side == 'B' else fix_oe_50.Side.Sell
    amend_request.TransactTime = hlp.get_time()
    amend_request.OrderQty = qty          # new total quantity (not a delta)
    amend_request.OrdType = fix_oe_50.OrdType.Limit
    amend_request.Price = price           # new price

    amend_request.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24}
    ]
    return amend_request
