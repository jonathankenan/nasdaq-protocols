import asyncio
import logging
import pytest
import random
import string
import datetime
import os

from datetime import datetime, timezone
from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Sending Order by input number of desired order ##

LOG_FILE = hlp.setup_logging()
# logging.basicConfig(level=logging.DEBUG)

@pytest.mark.asyncio
async def test_fix_multiple_orders():
    credentials = hlp.load_credentials('tests/idx_mme_data/pytest_credentials_fix.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_orders.csv')
    
    tasks = []
    for user in credentials:
        tasks.append(send_orders_for_user(user, orders))

    await asyncio.gather(*tasks)

async def send_orders_for_user(user, orders):
    fix_session = await hlp.loginFIXFromFile('172.18.2.132', '8200', user['username'], user['password'], user['sender_comp_id'])
    
    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        return

    current_time = hlp.get_time()

    order_idx = 0
    for i in range(user['order_count']):
        order = orders[order_idx % len(orders)]
        
        # logging.info(f"Sending order {i + 1} for user {user['username']}: {order}")
        logging.info(f"Sending order {i + 1} for user {user['username']} at {current_time}: {order}")

        enter_order = new_order(order['Symbol'], order['Price'], order['Side'], order['OrderQty'], user['username'], user['sender_comp_id'])
        
        enter_order.TransactTime = current_time
        
        logging.info(f"ClOrdID: {enter_order.ClOrdID}")
        
        fix_session.send_msg(enter_order)
        
        validate = await assert_order_placed(fix_session, enter_order)

        if validate is None:
            logging.error(f"Order {i + 1} for user {user['username']} failed validation.")
        else:
            logging.info(f"Order {i + 1} for user {user['username']} successfully placed.")
        
        order_idx += 1

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
    
    no_party_ids = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24}
    ]
    
    enter_order.NoPartyIDs = no_party_ids
    return enter_order