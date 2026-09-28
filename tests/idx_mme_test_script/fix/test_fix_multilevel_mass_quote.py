import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Send a mass quote with multiple price levels (same message as test_fix_mass_quote, but NoQuoteEntries > 1) ##

LOG_FILE = hlp.setup_logging()


def load_multilevel_quotes(file_path):
    # Format: symbol|bid_price|offer_price|qty -- 1 baris = 1 level, diisi manual
    levels = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 4:
                continue
            levels.append({
                'Symbol': parts[0],
                'BidPx': float(parts[1]),
                'OfferPx': float(parts[2]),
                'Qty': float(parts[3]),
            })
    return levels


@pytest.mark.asyncio
async def test_fix_multilevel_mass_quote():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_multilevel_mass_quote.csv')
    levels = load_multilevel_quotes('tests/idx_mme_data/data_multilevel_mass_quote.csv')

    user = credentials[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        mass_quote = new_multilevel_mass_quote(
            levels=levels,
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending multilevel MassQuote, QuoteID: {mass_quote.QuoteID}, "
                     f"levels: {len(levels)}")
        fix_session.send_msg(mass_quote)

        ack = await fix_session.receive_msg()
        logging.info(f"MassQuoteAck received: {ack}")

        assert isinstance(ack, fix_oe_50.MassQuoteAck), f"Unexpected response type: {ack}"
        assert ack.QuoteStatus == fix_oe_50.QuoteStatus.Accepted, \
            f"MassQuote rejected: {ack}"
        logging.info(f"MassQuote {mass_quote.QuoteID} with {len(levels)} levels accepted.")
    finally:
        await fix_session.close()


def new_multilevel_mass_quote(levels, username, sender_comp_id):
    # The best price level must be listed first; levels list is taken as-is from the CSV.
    quote_entries = []
    for level in levels:
        quote_entries.append({
            299: hlp.generate_ordertoken(),        # QuoteEntryID
            55: level['Symbol'],                    # Symbol
            132: level['BidPx'],                    # BidPx
            133: level['OfferPx'],                  # OfferPx
            134: level['Qty'],                      # BidSize
            135: level['Qty'],                      # OfferSize
            528: fix_oe_50.OrderCapacity.Agency,
        })

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
            302: '1',                       # QuoteSetID
            304: len(quote_entries),        # TotNoQuoteEntries
            295: quote_entries,              # NoQuoteEntries (multiple levels)
        }
    ]
    return mass_quote
