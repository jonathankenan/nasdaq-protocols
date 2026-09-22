import logging
import pytest

from nasdaq_mme_idx.de import ouch_de_gwy as ouch
from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper import ouch_utils as ouch_hlp

## Test case scenario: Amend (replace) an existing order via OUCH, based on spec 4.2.2/4.3.3/4.3.2 ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_ouch_amend_message():
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
        # 1. Place an order first, so there is something to amend
        enter_order = ouch_hlp.new_enter_order(
            order['Symbol'], order['Price'], order['Side'], order['OrderQty']
        )
        logging.info(f"Placing order to amend later, orderToken: {enter_order.orderToken}")
        ouch_session.send_message(enter_order)

        placed = await ouch_session.receive_message()
        logging.info(f"Order placed, response: {placed}")
        assert isinstance(placed, ouch.OuchOrderAccepted), \
            f"Order not accepted, cannot proceed to amend: {placed}"

        # 2. Amend the order: same qty, price moved up by 1
        new_price = order['Price'] + 1
        replace_order = ouch_hlp.new_replace_order(
            existing_token=enter_order.orderToken,
            quantity=order['OrderQty'],
            price=new_price,
        )
        logging.info(f"Sending replace for orderToken: {enter_order.orderToken}, "
                     f"replacementToken: {replace_order.replacementOrderToken}, new price: {new_price}")
        ouch_session.send_message(replace_order)

        response = await ouch_session.receive_message()
        logging.info(f"Amend response: {response}")

        if isinstance(response, ouch.OuchOrderRejected):
            assert False, f"Amend rejected, rejectCode: {response.rejectCode}"

        assert isinstance(response, ouch.OuchOrderReplaced), f"Unexpected response type: {response}"
        assert response.previousOrderToken == enter_order.orderToken, "previousOrderToken mismatch"
        assert response.replacementOrderToken == replace_order.replacementOrderToken, \
            "replacementOrderToken mismatch"
        logging.info(f"Order {enter_order.orderToken} successfully amended, "
                     f"new orderToken: {response.replacementOrderToken}")
    finally:
        await ouch_session.close()
