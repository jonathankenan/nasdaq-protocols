import logging

from nasdaq_mme_idx.de import ouch_de_gwy as ouch
from tests.idx_mme_helper import utils as hlp

# Helper for the OUCH test scripts, kept separate so the mentor's utils.py stays untouched.

OUCH_HOST = '172.18.2.162'   # dev6
OUCH_PORT = 8600

# UNCERTAIN: OUCH identifies an instrument by numeric orderBookId (from ITCH), not the FIX stock code -- placeholder below.
ORDER_BOOK_IDS = {
    'BANK_RG': 1,
}

CLIENT_ACCOUNT = 'CPD0812JVE87994\x00'   # same customer account as the FIX scripts, null-terminated per spec
ORDER_SOURCE = 'ABCD'                     # exchangeInfo: orderSource then settlementMethod


async def loginOUCH(hostname, port, username, password, session_id='', sequence=0):
    try:
        ouch_session = await ouch.connect_async(
            (hostname, port), username, password, session_id, sequence=sequence
        )
        logging.info(f"User {username} connected to OUCH successfully")
        return ouch_session
    except Exception as e:
        logging.error(f"Error during OUCH login for {username}: {e}")
        return None


def new_enter_order(symbol, price, side, quantity, order_token=None):
    order = ouch.OuchEnterOrder()
    order.orderToken = order_token if order_token is not None else int(hlp.generate_ordertoken())
    order.orderBookId = ORDER_BOOK_IDS[symbol]
    order.side = ouch.OuchSide.Buy if side == 'B' else ouch.OuchSide.Sell
    order.quantity = int(quantity)
    order.price = int(price)          # assumes 0 decimals for this order book
    order.timeInForce = ouch.OuchTimeInForce.Day
    order.openClose = 0
    order.clientAccount = CLIENT_ACCOUNT
    order.exchangeInfo = ORDER_SOURCE
    order.displayQuantity = 0
    order.orderType = ouch.OuchOrderType.Limit
    order.orderCapacity = ouch.OuchOrderCapacity.Agency
    order.selfMatchPreventionKey = 0
    order.attributes = ouch.OuchAttributes.Undefined
    return order


def new_cancel_order(order_token):
    cancel = ouch.OuchCancelOrder()
    cancel.orderToken = order_token
    return cancel


def new_replace_order(existing_token, quantity, price, replacement_token=None):
    # Fields meant to stay unchanged are left unset (0, or a leading null byte) so the order keeps its priority.
    replace = ouch.OuchReplaceOrder()
    replace.existingOrderToken = existing_token
    replace.replacementOrderToken = (
        replacement_token if replacement_token is not None else int(hlp.generate_ordertoken())
    )
    replace.quantity = int(quantity)   # desired TOTAL quantity, not a delta
    replace.price = int(price)         # assumes 0 decimals for this order book
    replace.openClose = 0
    replace.clientAccount = '\x00'
    replace.customerInfo = '\x00'
    replace.exchangeInfo = '\x00'
    replace.displayQuantity = 0
    replace.timeInForce = ouch.OuchTimeInForce.Undefined
    replace.timeInForceData = 0
    replace.selfMatchPreventionKey = 0
    return replace
