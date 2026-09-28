import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Send a mass quote, then cancel it via QuoteCancel ##

LOG_FILE = hlp.setup_logging()


def load_mass_quotes(file_path):
    # Format: symbol|bid_price|offer_price|bid_qty|offer_qty
    quotes = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 5:
                continue
            quotes.append({
                'Symbol': parts[0],
                'BidPx': float(parts[1]),
                'OfferPx': float(parts[2]),
                'BidQty': float(parts[3]),
                'OfferQty': float(parts[4]),
            })
    return quotes


@pytest.mark.asyncio
async def test_fix_withdraw_mass_quote():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    quotes = load_mass_quotes('tests/idx_mme_data/data_mass_quote.csv')

    user = credentials[0]
    quote_data = quotes[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        # 1. Place the quote first, so there is something to withdraw
        mass_quote = new_mass_quote(
            symbol=quote_data['Symbol'],
            bid_px=quote_data['BidPx'],
            offer_px=quote_data['OfferPx'],
            bid_qty=quote_data['BidQty'],
            offer_qty=quote_data['OfferQty'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending MassQuote to withdraw later, QuoteID: {mass_quote.QuoteID}")
        fix_session.send_msg(mass_quote)

        ack = await fix_session.receive_msg()
        logging.info(f"MassQuoteAck received: {ack}")
        assert isinstance(ack, fix_oe_50.MassQuoteAck), f"Unexpected response type: {ack}"
        assert ack.QuoteStatus == fix_oe_50.QuoteStatus.Accepted, \
            f"MassQuote not accepted, cannot proceed to withdraw: {ack}"

        # 2. Withdraw (cancel) the quote that was just placed
        cancel_request = new_quote_cancel(
            quote_id=mass_quote.QuoteID,
            symbol=quote_data['Symbol'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending QuoteCancel for QuoteID: {mass_quote.QuoteID}")
        fix_session.send_msg(cancel_request)

        cancel_ack = await fix_session.receive_msg()
        logging.info(f"QuoteCancel response: {cancel_ack}")

        assert isinstance(cancel_ack, fix_oe_50.MassQuoteAck), f"Unexpected response type: {cancel_ack}"
        # UNCERTAIN: exact QuoteStatus value on a successful cancel isn't confirmed yet.
        # Canceledforspecificsecurities matches our QuoteCancelType, Canceled is the generic value.
        cancel_statuses = {
            fix_oe_50.QuoteStatus.Canceledforspecificsecurities,
            fix_oe_50.QuoteStatus.Canceled,
        }
        assert cancel_ack.QuoteStatus in cancel_statuses, \
            f"QuoteCancel rejected: {cancel_ack}"
        logging.info(f"MassQuote {mass_quote.QuoteID} successfully withdrawn.")
    finally:
        await fix_session.close()


def new_mass_quote(symbol, bid_px, offer_px, bid_qty, offer_qty, username, sender_comp_id):
    mass_quote: fix_oe_50.MassQuote = fix_oe_50.MassQuote()
    mass_quote.QuoteID = hlp.generate_ordertoken()
    mass_quote.QuoteType = fix_oe_50.QuoteType.Tradeable
    mass_quote.QuoteResponseLevel = fix_oe_50.QuoteResponseLevel.AcknowledgeEachQuoteMessage

    mass_quote.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24},
    ]

    mass_quote.NoQuoteSets = [
        {
            302: '1',
            304: 1,
            295: [
                {
                    299: hlp.generate_ordertoken(),
                    55: symbol,
                    132: bid_px,
                    133: offer_px,
                    134: bid_qty,
                    135: offer_qty,
                    528: fix_oe_50.OrderCapacity.Agency,
                }
            ],
        }
    ]
    return mass_quote


def new_quote_cancel(quote_id, symbol, username, sender_comp_id):
    # Same party pattern as MassQuote/NewOrderSingle so the ExecutingFirm's order-source sub-group is present.
    cancel: fix_oe_50.QuoteCancel = fix_oe_50.QuoteCancel()
    cancel.QuoteID = quote_id
    cancel.QuoteCancelType = fix_oe_50.QuoteCancelType.CancelForOneOrMoreSecurities
    cancel.QuoteType = fix_oe_50.QuoteType.Tradeable

    cancel.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24},
    ]

    cancel.NoQuoteEntries = [
        {55: symbol}
    ]
    return cancel
