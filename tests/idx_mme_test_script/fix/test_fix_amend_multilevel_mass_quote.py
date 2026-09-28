import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Amend a multilevel mass quote by re-sending a new MassQuote with ##
## different prices per level for the same instrument/account. There is no dedicated ##
## "amend quote" message in FIX -- resending a MassQuote is the standard way to update it. ##

LOG_FILE = hlp.setup_logging()


def load_multilevel_quotes(file_path):
    # Format: symbol|bid_price|offer_price|bid_qty|offer_qty -- 1 baris = 1 level
    levels = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 5:
                continue
            levels.append({
                'Symbol': parts[0],
                'BidPx': float(parts[1]),
                'OfferPx': float(parts[2]),
                'BidQty': float(parts[3]),
                'OfferQty': float(parts[4]),
            })
    return levels


@pytest.mark.asyncio
async def test_fix_amend_multilevel_mass_quote():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_multilevel_mass_quote.csv')
    levels = load_multilevel_quotes('tests/idx_mme_data/data_multilevel_mass_quote.csv')
    amended_levels = load_multilevel_quotes('tests/idx_mme_data/data_amend_multilevel_mass_quote.csv')

    user = credentials[0]

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        # 1. Place the initial multilevel quote
        first_quote = new_multilevel_mass_quote(
            levels=levels,
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending initial multilevel MassQuote, QuoteID: {first_quote.QuoteID}")
        fix_session.send_msg(first_quote)

        ack = await fix_session.receive_msg()
        logging.info(f"Initial MassQuoteAck received: {ack}")
        assert isinstance(ack, fix_oe_50.MassQuoteAck), f"Unexpected response type: {ack}"
        assert ack.QuoteStatus == fix_oe_50.QuoteStatus.Accepted, \
            f"Initial MassQuote not accepted, cannot proceed to amend: {ack}"

        # 2. "Amend" by re-sending a new MassQuote for the same levels with new prices from CSV
        amend_quote = new_multilevel_mass_quote(
            levels=amended_levels,
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending amended multilevel MassQuote, QuoteID: {amend_quote.QuoteID}")
        fix_session.send_msg(amend_quote)

        amend_ack = await fix_session.receive_msg()
        logging.info(f"Amended MassQuoteAck received: {amend_ack}")

        assert isinstance(amend_ack, fix_oe_50.MassQuoteAck), f"Unexpected response type: {amend_ack}"
        assert amend_ack.QuoteStatus == fix_oe_50.QuoteStatus.Accepted, \
            f"Amended MassQuote rejected: {amend_ack}"
        logging.info(f"Multilevel MassQuote for {levels[0]['Symbol']} successfully amended (re-quoted).")
    finally:
        await fix_session.close()


def new_multilevel_mass_quote(levels, username, sender_comp_id):
    quote_entries = []
    for level in levels:
        quote_entries.append({
            299: hlp.generate_ordertoken(),
            55: level['Symbol'],
            132: level['BidPx'],
            133: level['OfferPx'],
            134: level['BidQty'],
            135: level['OfferQty'],
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
            302: '1',
            304: len(quote_entries),
            295: quote_entries,
        }
    ]
    return mass_quote
