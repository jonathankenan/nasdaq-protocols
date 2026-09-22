import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Amend (cancel/replace) an existing order, based on spec section 2.3 ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_fix_amend_message():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_limit.csv')

    user = credentials[0]
    order = orders[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.132', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        # 1. Place an order first, so there is something to amend
        enter_order = new_order(
            order['Symbol'], order['Price'], order['Side'], order['OrderQty'],
            user['username'], user['sender_comp_id']
        )
        logging.info(f"Placing order to amend later, ClOrdID: {enter_order.ClOrdID}")
        fix_session.send_msg(enter_order)

        placed_report = await fix_session.receive_msg()
        logging.info(f"Order placed, response: {placed_report}")
        assert placed_report.OrdStatus == fix_oe_50.OrdStatus.New, \
            f"Order not accepted, cannot proceed to amend: {placed_report}"

        # 2. Amend the order: same qty, price moved from 490 -> 491
        new_price = order['Price'] + 1
        amend_request = new_amend_request(
            orig_cl_ord_id=enter_order.ClOrdID,
            symbol=order['Symbol'],
            side=order['Side'],
            qty=order['OrderQty'],
            price=new_price,
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending amend request for OrigClOrdID: {enter_order.ClOrdID}, new price: {new_price}")
        fix_session.send_msg(amend_request)

        amend_response = await fix_session.receive_msg()
        logging.info(f"Amend response: {amend_response}")

        if isinstance(amend_response, fix_oe_50.OrderCancelReject):
            assert False, f"Amend rejected: {amend_response.RejectText}"

        assert amend_response.ExecType == fix_oe_50.ExecType.Replaced, \
            f"Unexpected ExecType after amend: {amend_response}"
        logging.info(f"Order {enter_order.ClOrdID} successfully amended, new ClOrdID: {amend_request.ClOrdID}")
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
