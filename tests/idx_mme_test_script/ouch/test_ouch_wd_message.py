import logging
import pytest

from nasdaq_mme_idx.de import ouch_de_gwy as ouch
from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper import ouch_utils as ouch_hlp

## Test case scenario: Withdraw (cancel) an existing order via OUCH, based on spec 4.2.3/4.3.4/4.3.2 ##

LOG_FILE = hlp.setup_logging()

CANCELED_BY_USER = 1   # cancelReason value from spec table 9

@pytest.mark.asyncio
async def test_ouch_wd_message():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit_ouch.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_limit.csv')

    user = credentials[0]
    order = orders[0]

    ouch_session = await ouch_hlp.loginOUCH(
        ouch_hlp.OUCH_HOST, ouch_hlp.OUCH_PORT, user['username'], user['password']
    )

    if not ouch_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        # 1. Place an order first, so there is something to withdraw
        enter_order = ouch_hlp.new_enter_order(
            order['Symbol'], order['Price'], order['Side'], order['OrderQty']
        )
        logging.info(f"Placing order to withdraw later, orderToken: {enter_order.orderToken}")
        ouch_session.send_message(enter_order)

        placed = await ouch_session.receive_message()
        logging.info(f"Order placed, response: {placed}")
        assert isinstance(placed, ouch.OuchOrderAccepted), \
            f"Order not accepted, cannot proceed to withdraw: {placed}"

        # 2. Withdraw the order that was just placed
        cancel_order = ouch_hlp.new_cancel_order(enter_order.orderToken)
        logging.info(f"Sending withdraw for orderToken: {enter_order.orderToken}")
        ouch_session.send_message(cancel_order)

        response = await ouch_session.receive_message()
        logging.info(f"Withdraw response: {response}")

        if isinstance(response, ouch.OuchOrderRejected):
            assert False, f"Withdraw rejected, rejectCode: {response.rejectCode}"

        assert isinstance(response, ouch.OuchOrderCanceled), f"Unexpected response type: {response}"
        assert response.orderToken == enter_order.orderToken, "orderToken mismatch in OrderCanceled"
        assert response.cancelReason == CANCELED_BY_USER, \
            f"Unexpected cancelReason: {response.cancelReason}"
        logging.info(f"Order {enter_order.orderToken} successfully withdrawn.")
    finally:
        await ouch_session.close()
