import asyncio
import logging
import pytest

from nasdaq_mme_idx import fix_oe_50
from tests.idx_mme_helper import utils as hlp

## Test case scenario: Report a 2-sided negotiated trade (Pasar Negosiasi), based on spec section 7.1/7.2 ##

LOG_FILE = hlp.setup_logging()

SECURITY_SUB_TYPE = '1'      # confirmed by mentor
SELLER_TRADER = 'ODJFE1'     # confirmed by mentor, real counterparty trader (different firm)
SELLER_FIRM = 'OD'           # confirmed by mentor, real counterparty firm

@pytest.mark.asyncio
async def test_fix_two_side():
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
        trade_report = new_trade_capture_report_2sided(
            symbol=order['Symbol'],
            price=order['Price'],
            qty=order['OrderQty'],
            buyer_trader=user['username'],
            buyer_firm=user['sender_comp_id'],
        )
        logging.info(f"Sending 2-sided TradeCaptureReport, TradeReportID: {trade_report.TradeReportID}")
        fix_session.send_msg(trade_report)

        ack = await fix_session.receive_msg()
        logging.info(f"TradeCaptureReportAck received: {ack}")

        assert isinstance(ack, fix_oe_50.TradeCaptureReportAck), f"Unexpected response type: {ack}"
        assert ack.TrdRptStatus == fix_oe_50.TrdRptStatus.Accepted, \
            f"Trade report rejected: {ack.RejectText if ack.TrdRptStatus == fix_oe_50.TrdRptStatus.Rejected else ack}"
        logging.info(f"TradeCaptureReport {trade_report.TradeReportID} accepted (MatchStatus: {ack.MatchStatus}).")
    finally:
        await fix_session.close()


def new_trade_capture_report_2sided(symbol, price, qty, buyer_trader, buyer_firm):
    trade_report: fix_oe_50.TradeCaptureReport = fix_oe_50.TradeCaptureReport()
    trade_report.TradeReportID = hlp.generate_ordertoken()
    trade_report.TradeReportType = fix_oe_50.TradeReportType.Submit
    trade_report.TradeHandlingInstr = fix_oe_50.TradeHandlingInstr.TwoPartyReport

    # Top-level Instrument is fixed for 2-sided reports; the real instrument is on the leg below (LegSymbol).
    trade_report.Symbol = '[N/A]'
    trade_report.SecurityType = fix_oe_50.SecurityType.MultilegInstrument
    trade_report.SecuritySubType = SECURITY_SUB_TYPE
    trade_report.SettlMethod = fix_oe_50.SettlMethod.DvPDeliveryvsPayment
    trade_report.TransactTime = hlp.get_time()

    trade_report.NoLegs = [
        {
            600: symbol,                            # LegSymbol
            624: fix_oe_50.LegSide.AsDefined,        # buyer buys, seller sells
            637: price,                              # LegLastPx
            1418: qty,                               # LegLastQty
        }
    ]

    trade_report.NoSides = [
        {
            54: fix_oe_50.Side.Buy,
            453: [
                {447: fix_oe_50.PartyIDSource.Proprietary, 448: buyer_trader, 452: 12},
                {802: [{523: 'ABCD', 803: 4030}], 447: fix_oe_50.PartyIDSource.Proprietary, 448: buyer_firm, 452: 1},
            ],
        },
        {
            54: fix_oe_50.Side.Sell,
            453: [
                {447: fix_oe_50.PartyIDSource.Proprietary, 448: SELLER_TRADER, 452: 12},
                {447: fix_oe_50.PartyIDSource.Proprietary, 448: SELLER_FIRM, 452: 1},
            ],
        },
    ]
    return trade_report
