"""
Test: kirim satu NewOrderSingle (limit order) ke IDX Eqlipse Trading (dev3)
dan tunggu ExecutionReport-nya.

Direkonstruksi dari:
- Konfigurasi dan Mapping File Pytest.docx (dev3 FIX: 172.18.2.132:8200)
- NDAQ_Trading_FIX_OE_ProtSpec_IDX.pdf (NewOrderSingle [D], ExecutionReport [8])

Data order & kredensial dibaca dari data_order_limit.csv dan
credential_order_limit.csv di folder yang sama.

CATATAN: field session-layer (Logon) di file messages.py memakai tag FIX
standard karena spesifikasi session/gateway ("FIX_SG") belum tersedia.
Kalau login gagal/di-reject, kemungkinan besar gateway IDX butuh field
tambahan di Logon (mis. ResetSeqNumFlag) -- perlu dikonfirmasi ke mentor/tim.
"""
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nasdaq_protocols import fix
from nasdaq_protocols.fix.session import Fix44Session

from . import messages as m


HERE = Path(__file__).parent
LOG_DIR = HERE / "log"

DEV3_FIX_HOST = "172.18.2.132"
DEV3_FIX_PORT = 8200

SIDE_MAP = {"B": "1", "S": "2"}
ORDER_TYPE_MAP = {"L": "2", "M": "1"}  # L=Limit, M=Market


def _read_pipe_csv(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        return next(reader)


def _now_transact_time() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H:%M:%S")


def _build_logon(user_id: str, password: str) -> m.Logon:
    return m.Logon({
        fix.MessageSegments.HEADER: {
            "SenderCompID": user_id,
            "TargetCompID": "IDX",
            "MsgSeqNum": 1,
        },
        fix.MessageSegments.BODY: {
            "EncryptMethod": 0,
            "HeartBtInt": 30,
            "Username": user_id,
            "Password": password,
        },
    })


def _build_new_order_single(cl_ord_id: str, sender_code: str, user_id: str,
                             stock_code: str, price: float, side: str,
                             qty: float, order_type: str) -> m.NewOrderSingle:
    order = m.NewOrderSingle({
        fix.MessageSegments.BODY: {
            "ClOrdID": cl_ord_id,
            # Parties is a repeating group (GroupContainer): it can only be
            # addressed by its FIX tag number (453) or its count-field name
            # ("NoPartyIDs"), not by the GroupContainer class name ("Parties")
            # -- attribute access (order.Parties = ...) does not work due to
            # how DataSegment resolves group names, so it's set here by tag.
            m.Parties.Tag: [
                {"PartyID": sender_code, "PartyIDSource": "D", "PartyRole": 1},   # ExecutingFirm
                {"PartyID": user_id, "PartyIDSource": "D", "PartyRole": 12},      # ExecutingTrader
            ],
            "Symbol": stock_code,
            "Side": SIDE_MAP[side],
            "TransactTime": _now_transact_time(),
            "OrderQty": qty,
            "OrdType": ORDER_TYPE_MAP[order_type],
            "TimeInForce": "0",  # Day
        },
    })
    if ORDER_TYPE_MAP[order_type] == "2":  # Limit needs a price
        order.Price = price
    return order


@pytest.mark.asyncio
async def test_fix_send_order_limit():
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    cred = _read_pipe_csv(HERE / "credential_order_limit.csv")
    order_data = _read_pipe_csv(HERE / "data_order_limit.csv")

    user_id = cred["user_id"]
    password = cred["password"]
    sender_code = cred["sender_code"]

    received: dict[str, fix.Message] = {}
    got_execution_report = asyncio.Event()

    async def on_msg(msg: fix.Message):
        if isinstance(msg, m.ExecutionReport):
            received["execution_report"] = msg
            got_execution_report.set()

    def _log(line: str):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"{stamp} | INFO | {line}"
        print(text)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    _log(f"Logging started - file: {log_path}")

    session = await fix.connect_async(
        (DEV3_FIX_HOST, DEV3_FIX_PORT),
        _build_logon(user_id, password),
        lambda: Fix44Session(on_msg_coro=on_msg),
    )
    _log(f"User {user_id} connected successfully")

    try:
        cl_ord_id = datetime.now().strftime("%H%M%S%f")
        order = _build_new_order_single(
            cl_ord_id=cl_ord_id,
            sender_code=sender_code,
            user_id=user_id,
            stock_code=order_data["stock_code"],
            price=float(order_data["price"]),
            side=order_data["side"],
            qty=float(order_data["qty"]),
            order_type=order_data["order_type"],
        )

        session.send_msg(order)
        _log(f"Sent order ClOrdID: {cl_ord_id} Symbol: {order_data['stock_code']} "
             f"Side: {order_data['side']} Qty: {order_data['qty']} Price: {order_data['price']}")

        await asyncio.wait_for(got_execution_report.wait(), timeout=10)
        report = received["execution_report"]
        _log(f"Received ExecutionReport OrderID: {report.OrderID} "
             f"OrdStatus: {report.OrdStatus} ExecType: {report.ExecType} "
             f"LeavesQty: {report.LeavesQty} CumQty: {report.CumQty}")

        assert report.OrdStatus not in m.REJECTED_ORD_STATUSES, (
            f"Order rejected: {report.Text if '58' in report.Body else report.as_collection()}"
        )
    finally:
        await session.close()
        _log("Session closed")
