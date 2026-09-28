import asyncio
import logging
import pytest

from datetime import datetime
from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

# Test case scenario: Sending Order with duration in minutes
# Fixed version of test_fix_send_order_time_duration.py: the original summary undercounts
# ExecutionReports because trailing reports still in flight when the loop ends are never
# read before the session closes. Fixed here by draining them, same fix as
# test_fix_send_order_time_range.py.

LOG_FILE = hlp.setup_logging()

@pytest.mark.asyncio
async def test_fix_multiple_orders_new():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_time_window.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_time_window.csv')

    tasks = []
    for user in credentials:
        duration_seconds = user['duration_minutes'] * 60
        tasks.append(send_orders_for_user(
            user, orders,
            duration_seconds=duration_seconds,
            delay_between_orders=0.05
        ))

    await asyncio.gather(*tasks)

async def send_orders_for_user(user, orders, duration_seconds=120, delay_between_orders=0.05):
    try:
        fix_session = await hlp.loginFIXFromFile('172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id'])
        if not fix_session:
            logging.error(f"Failed to connect for user {user['username']}.")
            return

        start_time = datetime.now()
        order_idx = 0
        send_count = 0
        status_count = {'8': 0, '0': 0, '1': 0, '2': 0, '4': 0, 'C': 0}
        symbol_count = {}
        # An order can get more than 1 ExecutionReport (e.g. New then Filled), so track
        # unique ClOrdIDs that got at least one report, instead of summing report counts.
        # Extra reports can also arrive for orders resting from a *previous* run (same-day,
        # never withdrawn) getting matched now -- those are expected, not a bug, so we only
        # check that every order WE sent this run got at least one report (subset check).
        sent_cl_ord_ids = set()
        reported_cl_ord_ids = set()

        logging.info(f"Start sending orders for {user['username']} at {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} for {user['duration_minutes']} minute(s)...")

        while (datetime.now() - start_time).total_seconds() < duration_seconds:
            order = orders[order_idx % len(orders)]
            current_time = datetime.now()

            enter_order = new_order(
                order['Symbol'],
                order['Price'],
                order['Side'],
                order['OrderQty'],
                order['OrderType'],
                user['username'],
                user['sender_comp_id']
            )
            enter_order.TransactTime = hlp.get_time()

            try:
                fix_session.send_msg(enter_order)
                send_count += 1
                sent_cl_ord_ids.add(enter_order.ClOrdID)

                symbol = enter_order.Symbol
                symbol_count[symbol] = symbol_count.get(symbol, 0) + 1

                logging.info(f"[{user['username']}] Sent order #{send_count} {enter_order.Symbol} ClOrdID: {enter_order.ClOrdID} at {current_time}")

                try:
                    exec_report = await fix_session.receive_msg()
                    if exec_report:
                        status = exec_report.OrdStatus
                        logging.info(f"[{user['username']}] Order: {exec_report.Symbol} ClOrdID: {exec_report.ClOrdID} price: {exec_report.Price} status: {exec_report.OrdStatus} at {current_time}")
                        if status in status_count:
                            status_count[status] += 1
                        reported_cl_ord_ids.add(exec_report.ClOrdID)
                except Exception as e:
                    logging.warning(f"[{user['username']}] No ExecutionReport or error reading response: {e}")

            except Exception as e:
                logging.error(f"Error sending order #{send_count} for {user['username']}: {e}")

            order_idx += 1
            await asyncio.sleep(delay_between_orders)

        # Drain any trailing ExecutionReports still in flight after the loop ends
        while True:
            try:
                exec_report = await asyncio.wait_for(fix_session.receive_msg(), timeout=1.0)
            except (asyncio.TimeoutError, EOFError):
                break
            if not exec_report:
                break
            status = exec_report.OrdStatus
            logging.info(
                f"[{user['username']}] Order: {exec_report.Symbol} ClOrdID: {exec_report.ClOrdID} "
                f"price: {exec_report.Price} status: {status} (drained after loop end)"
            )
            if status in status_count:
                status_count[status] += 1
            reported_cl_ord_ids.add(exec_report.ClOrdID)

        end_time = datetime.now()
        total_counted = sum(status_count.values())
        logging.info(
            f"[{user['username']}] SUMMARY STATUS --> "
            f"New(0): {status_count['0']}, "
            f"PartiallyFilled(1): {status_count['1']}, "
            f"Filled(2): {status_count['2']}, "
            f"Canceled(4): {status_count['4']}, "
            f"Rejected(8): {status_count['8']}, "
            f"Close(C): {status_count['C']}. Total counted: {total_counted}"
        )
        logging.info(f"[{user['username']}] SUMMARY ORDER PER SAHAM:")
        for sym, cnt in symbol_count.items():
            logging.info(f"[{user['username']}] {sym}: {cnt} order(s)")
        logging.info(f"Finished sending for {user['username']} \n Started Time at {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}. \n Finished Time at {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}. Total sent: {send_count} orders in {duration_seconds}s")

        missing = sent_cl_ord_ids - reported_cl_ord_ids
        assert not missing, \
            f"{len(missing)} of {send_count} orders never got any ExecutionReport: {missing}"

    except Exception as e:
        logging.error(f"Error in user task {user['username']}: {e}")
        raise
    finally:
        await close_session_safe(user, fix_session)

def new_order(Symbol, price, side, quantity, OrderType, username, sender_comp_id):
    enter_order: fix_oe_50.NewOrderSingle = fix_oe_50.NewOrderSingle()
    enter_order.Symbol = Symbol
    enter_order.Side = fix_oe_50.Side.Buy if side == 'B' else fix_oe_50.Side.Sell
    enter_order.OrderQty = quantity
    enter_order.OrdType = OrderType

    if OrderType == fix_oe_50.OrdType.Limit:
        enter_order.Price = price
        enter_order.TimeInForce = fix_oe_50.TimeInForce.Day
    elif OrderType == fix_oe_50.OrdType.Market:
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

async def close_session_safe(user, session):
    if not session:
        return
    try:
        await asyncio.sleep(0.5)
        if hasattr(session, "close"):
            await session.close()
        elif hasattr(session, "disconnect"):
            await session.disconnect()
        logging.info(f"{user['username']} session closed")
    except Exception as e:
        logging.warning(f"Error closing {user['username']} session: {e}")
