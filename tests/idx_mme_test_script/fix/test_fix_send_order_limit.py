import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Sending a single limit order (create order RG/TN) ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_fix_send_order_limit():
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
        enter_order = new_order(
            order['Symbol'], order['Price'], order['Side'], order['OrderQty'],
            user['username'], user['sender_comp_id']
        )
        enter_order.TransactTime = hlp.get_time()

        logging.info(f"ClOrdID: {enter_order.ClOrdID}")
        fix_session.send_msg(enter_order)

        validate = await assert_order_placed(fix_session, enter_order)

        if validate:
            logging.info(f"Order for user {user['username']} successfully placed.")
        else:
            logging.error(f"Order for user {user['username']} failed validation.")

        assert validate is True
    finally:
        await fix_session.close()


async def assert_order_placed(fix_session, enter_order):
    try:
        output_fix_execution_report = await fix_session.receive_msg()

        if not output_fix_execution_report:
            logging.error("No ExecutionReport received.")
            return None

        logging.info(f"Received ExecutionReport: {output_fix_execution_report}")

        if output_fix_execution_report.OrdStatus == fix_oe_50.OrdStatus.New:
            return True
        else:
            logging.error(f"Unexpected order status: {output_fix_execution_report.OrdStatus}")
            return False
    except Exception as e:
        logging.error(f"Error during validation: {e}")
        return None


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
