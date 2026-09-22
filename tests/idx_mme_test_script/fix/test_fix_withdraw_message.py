import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Withdraw (cancel) an existing order, based on spec section 2.4/2.5 ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_fix_withdraw_message():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_limit.csv')

    user = credentials[0]
    order = orders[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        # 1. Place an order first, so there is something to withdraw
        enter_order = new_order(
            order['Symbol'], order['Price'], order['Side'], order['OrderQty'],
            user['username'], user['sender_comp_id']
        )
        logging.info(f"Placing order to withdraw later, ClOrdID: {enter_order.ClOrdID}")
        fix_session.send_msg(enter_order)

        placed_report = await fix_session.receive_msg()
        logging.info(f"Order placed, response: {placed_report}")
        assert placed_report.OrdStatus == fix_oe_50.OrdStatus.New, \
            f"Order not accepted, cannot proceed to withdraw: {placed_report}"

        # 2. Withdraw (cancel) the order that was just placed
        cancel_request = new_cancel_request(
            orig_cl_ord_id=enter_order.ClOrdID,
            symbol=order['Symbol'],
            side=order['Side'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending withdraw request for OrigClOrdID: {enter_order.ClOrdID}")
        fix_session.send_msg(cancel_request)

        cancel_response = await fix_session.receive_msg()
        logging.info(f"Withdraw response: {cancel_response}")

        if isinstance(cancel_response, fix_oe_50.OrderCancelReject):
            assert False, f"Withdraw rejected: {cancel_response.RejectText}"

        assert cancel_response.OrdStatus == fix_oe_50.OrdStatus.Canceled, \
            f"Unexpected status after withdraw: {cancel_response}"
        logging.info(f"Order {enter_order.ClOrdID} successfully withdrawn.")
    finally:
        await fix_session.close()


def new_order(Symbol, price, side, quantity, username, sender_comp_id):
    enter_order: fix_oe_50.NewOrderSingle = fix_oe_50.NewOrderSingle()
    enter_order.Symbol = Symbol
    if side == 'B':
        enter_order.Side = fix_oe_50.Side.Buy
    elif side == 'S':
        enter_order.Side = fix_oe_50.Side.Sell
    enter_order.OrderQty = quantity
    enter_order.Price = price
    enter_order.OrdType = fix_oe_50.OrdType.Limit
    enter_order.TimeInForce = fix_oe_50.TimeInForce.Day

    cl_ord_id = hlp.generate_ordertoken()
    enter_order.ClOrdID = cl_ord_id
    logging.info(f"Generated ClOrdID: {cl_ord_id}")

    enter_order.TransactTime = hlp.get_time()
    enter_order.SecurityIDSource = fix_oe_50.SecurityIDSource.MarketplaceAssignedIdentifier
    enter_order.OrderCapacity = fix_oe_50.OrderCapacity.Agency

    enter_order.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24}
    ]
    return enter_order


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
