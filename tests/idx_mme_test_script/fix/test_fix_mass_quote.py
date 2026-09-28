import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Send a mass quote (1 instrument, 1 price level), based on spec section 3.1/3.2 ##

LOG_FILE = hlp.setup_logging()


def load_mass_quotes(file_path):
    # Format: symbol|bid_price|offer_price|qty -- bid/offer diisi manual, tidak dihitung dari price_fraction
    quotes = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 4:
                continue
            quotes.append({
                'Symbol': parts[0],
                'BidPx': float(parts[1]),
                'OfferPx': float(parts[2]),
                'Qty': float(parts[3]),
            })
    return quotes


@pytest.mark.asyncio
async def test_fix_mass_quote():
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
        mass_quote = new_mass_quote(
            symbol=quote_data['Symbol'],
            bid_px=quote_data['BidPx'],
            offer_px=quote_data['OfferPx'],
            size=quote_data['Qty'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending MassQuote, QuoteID: {mass_quote.QuoteID}")
        fix_session.send_msg(mass_quote)

        ack = await fix_session.receive_msg()
        logging.info(f"MassQuoteAck received: {ack}")

        assert isinstance(ack, fix_oe_50.MassQuoteAck), f"Unexpected response type: {ack}"
        assert ack.QuoteStatus == fix_oe_50.QuoteStatus.Accepted, \
            f"MassQuote rejected: {ack}"
        logging.info(f"MassQuote {mass_quote.QuoteID} accepted.")
    finally:
        await fix_session.close()


def new_mass_quote(symbol, bid_px, offer_px, size, username, sender_comp_id):
    mass_quote: fix_oe_50.MassQuote = fix_oe_50.MassQuote()
    mass_quote.QuoteID = hlp.generate_ordertoken()
    mass_quote.QuoteType = fix_oe_50.QuoteType.Tradeable
    # A successful MassQuote gets no ack by default, so force one here.
    mass_quote.QuoteResponseLevel = fix_oe_50.QuoteResponseLevel.AcknowledgeEachQuoteMessage

    mass_quote.NoPartyIDs = [
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},
        {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},
        {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24},
    ]

    mass_quote.NoQuoteSets = [
        {
            302: '1',           # QuoteSetID
            304: 1,             # TotNoQuoteEntries
            295: [              # NoQuoteEntries
                {
                    299: hlp.generate_ordertoken(),   # QuoteEntryID
                    55: symbol,                        # Symbol
                    132: bid_px,                        # BidPx
                    133: offer_px,                       # OfferPx
                    134: size,                          # BidSize
                    135: size,                          # OfferSize
                    528: fix_oe_50.OrderCapacity.Agency,
                }
            ],
        }
    ]
    return mass_quote
