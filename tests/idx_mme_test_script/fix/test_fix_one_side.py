import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Report a 1-sided negotiated trade (Pasar Negosiasi), based on spec section 6.1/6.2 ##

LOG_FILE = hlp.setup_logging()

SECURITY_SUB_TYPE = 'NEGO'   # placeholder, confirm real code with mentor
CONTRA_FIRM = 'XA'           # placeholder counterparty firm CompID

@pytest.mark.asyncio
async def test_fix_one_side():
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
        trade_report = new_trade_capture_report_1sided(
            symbol=order['Symbol'],
            price=order['Price'],
            side=order['Side'],
            qty=order['OrderQty'],
            username=user['username'],
            sender_comp_id=user['sender_comp_id'],
        )
        logging.info(f"Sending 1-sided TradeCaptureReport, TradeReportID: {trade_report.TradeReportID}")
        fix_session.send_msg(trade_report)

        ack = await fix_session.receive_msg()
        logging.info(f"TradeCaptureReportAck received: {ack}")

        assert isinstance(ack, fix_oe_50.TradeCaptureReportAck), f"Unexpected response type: {ack}"
        assert ack.TrdRptStatus == fix_oe_50.TrdRptStatus.Accepted, \
            f"Trade report rejected: {ack.RejectText if ack.TrdRptStatus == fix_oe_50.TrdRptStatus.Rejected else ack}"
        logging.info(f"TradeCaptureReport {trade_report.TradeReportID} accepted (MatchStatus: {ack.MatchStatus}).")
    finally:
        await fix_session.close()


def new_trade_capture_report_1sided(symbol, price, side, qty, username, sender_comp_id):
    trade_report: fix_oe_50.TradeCaptureReport = fix_oe_50.TradeCaptureReport()
    trade_report.TradeReportID = hlp.generate_ordertoken()
    trade_report.TradeReportType = fix_oe_50.TradeReportType.Submit
    trade_report.TradeHandlingInstr = fix_oe_50.TradeHandlingInstr.OnePartyReportForMatching

    trade_report.Symbol = symbol
    # SecurityType is unused by Eqlipse Trading but the FIX dictionary still requires it.
    trade_report.SecurityType = fix_oe_50.SecurityType.NoSecurityType
    trade_report.SecuritySubType = SECURITY_SUB_TYPE
    trade_report.SettlMethod = fix_oe_50.SettlMethod.DvPDeliveryvsPayment
    trade_report.LastQty = qty
    trade_report.LastPx = price
    trade_report.TransactTime = hlp.get_time()

    trade_report.NoSides = [
        {
            54: fix_oe_50.Side.Buy if side == 'B' else fix_oe_50.Side.Sell,
            453: [   # our identity + the counterparty firm (ContraFirm=17)
                {447: fix_oe_50.PartyIDSource.Proprietary, 448: username, 452: 12},           # ExecutingTrader
                {447: fix_oe_50.PartyIDSource.Proprietary, 448: sender_comp_id, 452: 1},      # ExecutingFirm
                {447: fix_oe_50.PartyIDSource.Proprietary, 448: 'CPD0812JVE87994', 452: 24},  # CustomerAccount
                {447: fix_oe_50.PartyIDSource.Proprietary, 448: CONTRA_FIRM, 452: 17},        # ContraFirm
            ],
        }
    ]
    return trade_report
