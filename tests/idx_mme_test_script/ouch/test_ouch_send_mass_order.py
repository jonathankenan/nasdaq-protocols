import logging
import pytest

from nasdaq_mme_idx.de import ouch_de_gwy as ouch
from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper import ouch_utils as ouch_hlp

## Test case scenario: Sending orders via OUCH, as many as the desired order count (same idea as test_fix_send_multi_orders) ##

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_ouch_send_mass_order():
    credentials = hlp.load_credentials('tests/idx_mme_data/pytest_credentials_ouch.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_limit.csv')

    user = credentials[0]

    ouch_session = await ouch_hlp.loginOUCH(
        ouch_hlp.OUCH_HOST, ouch_hlp.OUCH_PORT, user['username'], user['password']
    )

    if not ouch_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    accepted = 0
    rejected = 0
    # Sequential tokens so none collide within this run
    base_token = int(hlp.generate_ordertoken()) * 1000

    try:
        for i in range(user['order_count']):
            order = orders[i % len(orders)]
            enter_order = ouch_hlp.new_enter_order(
                order['Symbol'], order['Price'], order['Side'], order['OrderQty'],
                order_token=base_token + i,
            )
            logging.info(f"Sending order {i + 1} for user {user['username']}, orderToken: {enter_order.orderToken}")
            ouch_session.send_message(enter_order)

            response = await ouch_session.receive_message()
            if isinstance(response, ouch.OuchOrderAccepted):
                accepted += 1
                logging.info(f"Order {i + 1} for user {user['username']} successfully placed.")
            elif isinstance(response, ouch.OuchOrderRejected):
                rejected += 1
                logging.error(f"Order {i + 1} for user {user['username']} rejected, "
                              f"rejectCode: {response.rejectCode}")
            else:
                logging.error(f"Order {i + 1} unexpected response: {response}")

        logging.info(f"SUMMARY [{user['username']}] --> Accepted: {accepted}, Rejected: {rejected}, "
                     f"Target: {user['order_count']}")
        assert accepted == user['order_count'], \
            f"Only {accepted} of {user['order_count']} orders accepted ({rejected} rejected)"
    finally:
        await ouch_session.close()
