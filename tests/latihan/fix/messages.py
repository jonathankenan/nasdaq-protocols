"""
FIX message definitions for IDX Eqlipse Trading Order Entry (OE-IDX-i / OE-IDX-o).

Rebuilt from the official spec:
"Nasdaq Eqlipse Trading - FIX Specification for Order, Quote, and Trade
Report Entry - IDX", revision 2.2.121 (29 Jul 2025), sections 2.1
(NewOrderSingle) and 2.2 (ExecutionReport).

Only the subset of tags needed for a plain limit order (test_fix_send_order_limit)
is included. Extend this file (OrderCancelReplaceRequest, OrderCancelRequest,
MassQuote, Quote, ...) as more test scripts are rebuilt.
"""
from nasdaq_protocols import fix


# --- Standard header/trailer fields (FIX standard, same for every message) ---
class BeginString(fix.Field, Tag=8, Name="BeginString", Type=fix.FixString):
    ...


class BodyLength(fix.Field, Tag=9, Name="BodyLength", Type=fix.FixInt):
    ...


class MsgType(fix.Field, Tag=35, Name="MsgType", Type=fix.FixString):
    ...


class SenderCompID(fix.Field, Tag=49, Name="SenderCompID", Type=fix.FixString):
    ...


class TargetCompID(fix.Field, Tag=56, Name="TargetCompID", Type=fix.FixString):
    ...


class MsgSeqNum(fix.Field, Tag=34, Name="MsgSeqNum", Type=fix.FixInt):
    ...


class SenderSubID(fix.Field, Tag=50, Name="SenderSubID", Type=fix.FixString):
    ...


class TargetSubID(fix.Field, Tag=57, Name="TargetSubID", Type=fix.FixString):
    ...


class SendingTime(fix.Field, Tag=52, Name="SendingTime", Type=fix.FixUTCTimeStamp):
    ...


class CheckSum(fix.Field, Tag=10, Name="CheckSum", Type=fix.FixString):
    ...


class Header(fix.DataSegment):
    Entries = [
        fix.Entry(BeginString, True),
        fix.Entry(BodyLength, True),
        fix.Entry(MsgType, True),
        fix.Entry(SenderCompID, True),
        fix.Entry(TargetCompID, True),
        fix.Entry(MsgSeqNum, True),
        fix.Entry(SenderSubID, False),
        fix.Entry(TargetSubID, False),
        fix.Entry(SendingTime, True),
    ]


class Trailer(fix.DataSegment):
    Entries = [
        fix.Entry(CheckSum, True),
    ]


# --- Logon (A) ---
# NOTE: session-layer (Logon/Logout/Heartbeat) is NOT covered by the Order
# Entry spec we have (it lives in a separate "FIX_SG" session/gateway spec
# we don't have). Fields below are the FIX-standard Logon(A) fields; confirm
# with mentor/team if the real gateway expects extra tags.
class EncryptMethod(fix.Field, Tag=98, Name="EncryptMethod", Type=fix.FixInt):
    ...


class HeartBtInt(fix.Field, Tag=108, Name="HeartBtInt", Type=fix.FixInt):
    ...


class Username(fix.Field, Tag=553, Name="Username", Type=fix.FixString):
    ...


class Password(fix.Field, Tag=554, Name="Password", Type=fix.FixString):
    ...


class LogonBody(fix.DataSegment):
    Entries = [
        fix.Entry(EncryptMethod, True),
        fix.Entry(HeartBtInt, True),
        fix.Entry(Username, True),
        fix.Entry(Password, True),
    ]


class Logon(fix.Message,
            Name='Logon',
            Type='A',
            Category='Session',
            HeaderCls=Header,
            BodyCls=LogonBody,
            TrailerCls=Trailer):
    ...


class Logout(fix.Message,
             Name='Logout',
             Type='5',
             Category='Session',
             HeaderCls=Header,
             BodyCls=fix.DataSegment,
             TrailerCls=Trailer):
    ...


# --- Parties group (tag 453), used by NewOrderSingle & ExecutionReport ---
# PartyRole values used for order entry (Table 1 in the spec):
#   1  = ExecutingFirm     (Y, Req'd)
#   12 = ExecutingTrader   (Y, Req'd)
#   24 = CustomerAccount
#   7  = EnteringFirm      (Cond'l)
#   36 = EnteringTrader    (Cond'l)
class PartyID(fix.Field, Tag=448, Name="PartyID", Type=fix.FixString):
    ...


class PartyIDSource(fix.Field, Tag=447, Name="PartyIDSource", Type=fix.FixChar):
    ...


class PartyRole(fix.Field, Tag=452, Name="PartyRole", Type=fix.FixInt):
    ...


class NoPartyIDs(fix.Field, Tag=453, Name="NoPartyIDs", Type=fix.FixInt):
    ...


class PartiesGroup(fix.Group):
    Entries = [
        fix.Entry(PartyID, True),
        fix.Entry(PartyIDSource, True),
        fix.Entry(PartyRole, True),
    ]


class Parties(fix.GroupContainer, CountCls=NoPartyIDs, GroupCls=PartiesGroup):
    ...


# --- NewOrderSingle (D), in (OE-IDX-i) --- spec section 2.1 / Table 3 ---
class ClOrdID(fix.Field, Tag=11, Name="ClOrdID", Type=fix.FixString):
    ...


class Symbol(fix.Field, Tag=55, Name="Symbol", Type=fix.FixString):
    ...


class Side(fix.Field, Tag=54, Name="Side", Type=fix.FixChar):
    ...
    # 1 = Buy, 2 = Sell, 5 = SellShort


class TransactTime(fix.Field, Tag=60, Name="TransactTime", Type=fix.FixUTCTimeStamp):
    ...


class OrderQty(fix.Field, Tag=38, Name="OrderQty", Type=fix.FixQuantity):
    ...


class OrdType(fix.Field, Tag=40, Name="OrdType", Type=fix.FixChar):
    ...
    # 1 = Market, 2 = Limit, K = MarketWithLeftOverAsLimit, P = Pegged


class Price(fix.Field, Tag=44, Name="Price", Type=fix.FixPrice):
    ...


class TimeInForce(fix.Field, Tag=59, Name="TimeInForce", Type=fix.FixChar):
    ...
    # 0 = Day, 1 = GTC, 3 = IOC, 4 = FOK, 6 = GTD


class Text(fix.Field, Tag=58, Name="Text", Type=fix.FixString):
    ...


class NewOrderSingleBody(fix.DataSegment):
    Entries = [
        fix.Entry(ClOrdID, True),
        fix.Entry(Parties, True),
        fix.Entry(Symbol, True),
        fix.Entry(Side, True),
        fix.Entry(TransactTime, True),
        fix.Entry(OrderQty, True),
        fix.Entry(OrdType, True),
        fix.Entry(Price, False),
        fix.Entry(TimeInForce, False),
        fix.Entry(Text, False),
    ]


class NewOrderSingle(fix.Message,
                      Name='NewOrderSingle',
                      Type='D',
                      Category='OrderEntry',
                      HeaderCls=Header,
                      BodyCls=NewOrderSingleBody,
                      TrailerCls=Trailer):
    ...


# --- ExecutionReport (8), out (OE-IDX-o) --- spec section 2.2 / Table 4 ---
class OrderID(fix.Field, Tag=37, Name="OrderID", Type=fix.FixString):
    ...


class OrigClOrdID(fix.Field, Tag=41, Name="OrigClOrdID", Type=fix.FixString):
    ...


class ExecID(fix.Field, Tag=17, Name="ExecID", Type=fix.FixString):
    ...


class ExecType(fix.Field, Tag=150, Name="ExecType", Type=fix.FixChar):
    ...
    # 0=New 4=Canceled 5=Replaced 8=Rejected C=Expired D=Restated F=Trade


class OrdStatus(fix.Field, Tag=39, Name="OrdStatus", Type=fix.FixChar):
    ...
    # 0=New 1=PartiallyFilled 2=Filled 4=Canceled 8=Rejected C=Expired


class LeavesQty(fix.Field, Tag=151, Name="LeavesQty", Type=fix.FixQuantity):
    ...


class CumQty(fix.Field, Tag=14, Name="CumQty", Type=fix.FixQuantity):
    ...


class RejectText(fix.Field, Tag=1328, Name="RejectText", Type=fix.FixString):
    ...


class ExecutionReportBody(fix.DataSegment):
    Entries = [
        fix.Entry(OrderID, True),
        fix.Entry(ClOrdID, False),
        fix.Entry(OrigClOrdID, False),
        fix.Entry(Parties, False),
        fix.Entry(ExecID, True),
        fix.Entry(ExecType, True),
        fix.Entry(OrdStatus, True),
        fix.Entry(RejectText, False),
        fix.Entry(Symbol, True),
        fix.Entry(Side, True),
        fix.Entry(OrderQty, False),
        fix.Entry(OrdType, False),
        fix.Entry(Price, False),
        fix.Entry(LeavesQty, True),
        fix.Entry(CumQty, True),
        fix.Entry(Text, False),
    ]


class ExecutionReport(fix.Message,
                       Name='ExecutionReport',
                       Type='8',
                       Category='OrderEntry',
                       HeaderCls=Header,
                       BodyCls=ExecutionReportBody,
                       TrailerCls=Trailer):
    ...


# OrdStatus / ExecType values that mean the order was accepted (not rejected)
ACCEPTED_ORD_STATUSES = {'0', '1', '2'}    # New, PartiallyFilled, Filled
REJECTED_ORD_STATUSES = {'8'}              # Rejected
