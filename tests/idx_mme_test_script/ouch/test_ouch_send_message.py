import logging
import pytest

from nasdaq_mme_idx.de import ouch_de_gwy as ouch
from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper import ouch_utils as ouch_hlp

## Test case scenario: Send a single limit order via OUCH (create order RG/TN), based on spec 4.2.1/4.3.1/4.3.2 ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_ouch_send_message():
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
        enter_order = ouch_hlp.new_enter_order(
            order['Symbol'], order['Price'], order['Side'], order['OrderQty']
        )
        logging.info(f"Sending OUCH EnterOrder, orderToken: {enter_order.orderToken}")
        ouch_session.send_message(enter_order)

        response = await ouch_session.receive_message()
        logging.info(f"Response received: {response}")

        if isinstance(response, ouch.OuchOrderRejected):
            assert False, f"Order rejected, rejectCode: {response.rejectCode}"

        assert isinstance(response, ouch.OuchOrderAccepted), f"Unexpected response type: {response}"
        assert response.orderToken == enter_order.orderToken, "orderToken mismatch in OrderAccepted"
        logging.info(f"Order {enter_order.orderToken} accepted, orderId: {response.orderId}")
    finally:
        await ouch_session.close()
