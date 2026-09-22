import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Send a mass quote with multiple price levels (same message as test_fix_mass_quote, but NoQuoteEntries > 1) ##

LOG_FILE = hlp.setup_logging()

# 3 price levels: (offset from base price, size)
PRICE_LEVELS = [
    (1, 1.0),
    (2, 1.0),
    (3, 1.0),
]

@pytest.mark.asyncio
async def test_fix_multilevel_mass_quote():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_order_limit.csv')
    orders = hlp.load_orders('tests/idx_mme_data/data_order_limit.csv')

    user = credentials[0]
    order = orders[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        mass_quote = new_multilevel_mass_quote(
            symbol=order['Symbol'],
            base_price=order['Price'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending multilevel MassQuote, QuoteID: {mass_quote.QuoteID}, "
                     f"levels: {len(PRICE_LEVELS)}")
        fix_session.send_msg(mass_quote)

        ack = await fix_session.receive_msg()
        logging.info(f"MassQuoteAck received: {ack}")

        assert isinstance(ack, fix_oe_50.MassQuoteAck), f"Unexpected response type: {ack}"
        assert ack.QuoteStatus == fix_oe_50.QuoteStatus.Accepted, \
            f"MassQuote rejected: {ack}"
        logging.info(f"MassQuote {mass_quote.QuoteID} with {len(PRICE_LEVELS)} levels accepted.")
    finally:
        await fix_session.close()


def new_multilevel_mass_quote(symbol, base_price, username, sender_comp_id):
    # The best price level must be listed first.
    quote_entries = []
    for offset, size in PRICE_LEVELS:
        quote_entries.append({
            299: hlp.generate_ordertoken(),        # QuoteEntryID
            55: symbol,                             # Symbol
            132: base_price - offset,               # BidPx (gets lower each level)
            133: base_price + offset,               # OfferPx (gets higher each level)
            134: size,                              # BidSize
            135: size,                              # OfferSize
            528: fix_oe_50.OrderCapacity.Agency,
        })

    mass_quote: fix_oe_50.MassQuote = fix_oe_50.MassQuote()
    mass_quote.QuoteID = hlp.generate_ordertoken()
    mass_quote.QuoteType = fix_oe_50.QuoteType.Tradeable
    mass_quote.QuoteResponseLevel = fix_oe_50.QuoteResponseLevel.AcknowledgeEachQuoteMessage

    mass_quote.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
    ]

    mass_quote.NoQuoteSets = [
        {
            302: '1',                       # QuoteSetID
            304: len(quote_entries),        # TotNoQuoteEntries
            295: quote_entries,              # NoQuoteEntries (multiple levels)
        }
    ]
    return mass_quote
