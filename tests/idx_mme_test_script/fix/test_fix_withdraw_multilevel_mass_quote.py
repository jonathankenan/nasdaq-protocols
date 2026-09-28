import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp
from tests.idx_mme_helper.state import load_state

## Test case scenario: Cancel an existing multilevel mass quote via QuoteCancel ##
## Requires a quote already placed by test_fix_multilevel_mass_quote.py in a separate run. ##

LOG_FILE = hlp.setup_logging()


@pytest.mark.asyncio
async def test_fix_withdraw_multilevel_mass_quote():
    credentials = hlp.load_credentials('tests/idx_mme_data/credential_multilevel_mass_quote.csv')

    user = credentials[0]

    try:
        existing_quote = load_state('multilevel_mass_quote')
    except FileNotFoundError:
        assert False, "No existing quote found. Run test_fix_multilevel_mass_quote.py first."

    fix_session = await hlp.loginFIXFromFile(
        '172.18.2.162', '8200', user['username'], user['password'], user['sender_comp_id']
    )

    if not fix_session:
        logging.error(f"Failed to connect for user {user['username']}.")
        assert False, "Failed to connect/login."

    try:
        # Withdraw (cancel) the quote placed earlier by test_fix_multilevel_mass_quote.py.
        cancel_request = new_quote_cancel(
            quote_id=existing_quote['QuoteID'],
            symbol=existing_quote['Symbol'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending QuoteCancel for QuoteID: {existing_quote['QuoteID']}")
        fix_session.send_msg(cancel_request)

        cancel_ack = await fix_session.receive_msg()
        logging.info(f"QuoteCancel response: {cancel_ack}")

        assert isinstance(cancel_ack, fix_oe_50.QuoteStatusReport), f"Unexpected response type: {cancel_ack}"
        # UNCERTAIN: exact QuoteStatus value on a successful cancel isn't confirmed yet.
        cancel_statuses = {
            fix_oe_50.QuoteStatus.Canceledforspecificsecurities,
            fix_oe_50.QuoteStatus.Canceled,
        }
        assert cancel_ack.QuoteStatus in cancel_statuses, \
            f"QuoteCancel rejected: {cancel_ack}"
        logging.info(f"MassQuote {existing_quote['QuoteID']} successfully withdrawn.")
    finally:
        await fix_session.close()


def new_quote_cancel(quote_id, symbol, username, sender_comp_id):
    cancel: fix_oe_50.QuoteCancel = fix_oe_50.QuoteCancel()
    # QuoteReqID is marked optional in the generic FIX dictionary, but MME rejects the message without it.
    cancel.QuoteReqID = hlp.generate_ordertoken()
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
