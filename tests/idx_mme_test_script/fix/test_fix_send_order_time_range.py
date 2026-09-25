import asyncio
import logging
from datetime import datetime, timedelta
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Sending orders only within a specific start-end time window (not just for N minutes) ##

LOG_FILE = hlp.setup_logging()

START_DELAY_SECONDS = 1     # window opens this many seconds after the test starts
WINDOW_LENGTH_SECONDS = 5   # window stays open this long
DELAY_BETWEEN_ORDERS = 0.5

@pytest.mark.asyncio
async def test_fix_send_order_time_range():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_time_window.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_time_window.csv')

    user = credentials[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )
    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    start_time = datetime.now() + timedelta(seconds=START_DELAY_SECONDS)
    end_time = start_time + timedelta(seconds=WINDOW_LENGTH_SECONDS)
    logging.info(
        f"Order window for {user['username']}: "
        f"{start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}"
    )

    order_idx = 0
    send_count = 0
    status_count = {'8': 0, '0': 0, '1': 0, '2': 0, '4': 0, 'C': 0}

    try:
        wait_seconds = (start_time - datetime.now()).total_seconds()
        if wait_seconds > 0:
            logging.info(f"Waiting {wait_seconds:.1f}s for the window to open...")
            await asyncio.sleep(wait_seconds)

        while datetime.now() < end_time:
            order = orders[order_idx % len(orders)]

            enter_order = new_order(
                order['Symbol'], order['Price'], order['Side'], order['OrderQty'],
                order['OrderType'], user['username'], user['sender_comp_id']
            )

            try:
                fix_session.send_msg(enter_order)
                send_count += 1
                logging.info(
                    f"[{user['username']}] Sent order #{send_count} {enter_order.Symbol} "
                    f"ClOrdID: {enter_order.ClOrdID}"
                )

                try:
                    exec_report = await fix_session.receive_msg()
                    if exec_report:
                        status = exec_report.OrdStatus
                        logging.info(
                            f"[{user['username']}] Order: {exec_report.Symbol} "
                            f"ClOrdID: {exec_report.ClOrdID} status: {status}"
                        )
                        if status in status_count:
                            status_count[status] += 1
                except Exception as e:
                    logging.warning(f"[{user['username']}] No ExecutionReport or error reading response: {e}")

            except Exception as e:
                logging.error(f"Error sending order #{send_count} for {user['username']}: {e}")

            order_idx += 1
            await asyncio.sleep(DELAY_BETWEEN_ORDERS)

        # Drain any trailing ExecutionReports still in flight after the window closes
        while True:
            try:
                exec_report = await asyncio.wait_for(fix_session.receive_msg(), timeout=1.0)
            except asyncio.TimeoutError:
                break
            if not exec_report:
                break
            status = exec_report.OrdStatus
            logging.info(
                f"[{user['username']}] Order: {exec_report.Symbol} "
                f"ClOrdID: {exec_report.ClOrdID} status: {status} (drained after window close)"
            )
            if status in status_count:
                status_count[status] += 1

        logging.info(
            f"[{user['username']}] SUMMARY STATUS --> "
            f"New(0): {status_count['0']}, Rejected(8): {status_count['8']}, "
            f"Filled(1): {status_count['1']}, Canceled(4): {status_count['4']}, "
            f"Close(C): {status_count['C']}. Total sent: {send_count}"
        )
        assert send_count > 0, "No orders were sent within the time window."
    finally:
        await fix_session.close()


def new_order(Symbol, price, side, quantity, order_type, username, sender_comp_id):
    enter_order: fix_oe_50.NewOrderSingle = fix_oe_50.NewOrderSingle()
    enter_order.Symbol = Symbol
    enter_order.Side = fix_oe_50.Side.Buy if side == 'B' else fix_oe_50.Side.Sell
    enter_order.OrderQty = quantity
    enter_order.OrdType = order_type

    if order_type == fix_oe_50.OrdType.Limit:
        enter_order.Price = price
        enter_order.TimeInForce = fix_oe_50.TimeInForce.Day
    elif order_type == fix_oe_50.OrdType.Market:
        enter_order.TimeInForce = fix_oe_50.TimeInForce.ImmediateOrCancel

    cl_ord_id = hlp.generate_ordertoken()
    enter_order.ClOrdID = cl_ord_id
    enter_order.TransactTime = hlp.get_time()
    enter_order.SecurityIDSource = fix_oe_50.SecurityIDSource.MarketplaceAssignedIdentifier
    enter_order.OrderCapacity = fix_oe_50.OrderCapacity.Agency

    enter_order.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24}
    ]
    return enter_order
