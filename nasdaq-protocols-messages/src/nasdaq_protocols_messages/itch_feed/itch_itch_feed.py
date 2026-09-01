import asyncio
from enum import Enum
from typing import Callable, Awaitable, Type

import click
from nasdaq_protocols.common import utils
from nasdaq_protocols.common import logable
from nasdaq_protocols.common.message import *
from nasdaq_protocols import soup, itch


__all__ = [
    'Message',
    'ClientSession',
    'connect_async',
    'tail_messages',
    'ItchSide',
    'SystemEventCode',
    'TradingState',
    'SystemEvent',
    'StockTradingAction',
    'AddOrder',
    'OrderExecuted',
    'OrderCancel',
    'OrderDelete',
    'Trade',
]


@logable
class Message(itch.Message, app_name='itch_feed'):
    def __init_subclass__(cls, **kwargs):
        cls.log.debug('subclassing %s, params = %s', cls.__name__, str(kwargs))
        if 'indicator' not in kwargs:
            raise ValueError('expected "indicator" when subclassing itch_feed.Message')

        kwargs['app_name'] = 'itch_feed'
        super().__init_subclass__(**kwargs)


class ClientSession(itch.ClientSession):
    @classmethod
    def decode(cls, bytes_: bytes) -> [int, Message]:
        return Message.from_bytes(bytes_)


async def connect_async(remote: tuple[str, int], user: str, passwd: str, session_id,
                        sequence: int = 0,
                        session_factory: Callable[[soup.SoupClientSession], ClientSession] = None,
                        on_msg_coro: Callable[[Type[Message]], Awaitable[None]] = None,
                        on_close_coro: Callable[[], Awaitable[None]] = None,
                        client_heartbeat_interval: int = 10,
                        server_heartbeat_interval: int = 10,
                        connect_timeout: int = 5) -> ClientSession:
    if session_factory is None:
        def session_factory(x):
            return ClientSession(x, on_msg_coro=on_msg_coro, on_close_coro=on_close_coro)

    return await itch.connect_async(
        remote, user, passwd, session_id, sequence,
        session_factory, on_msg_coro, on_close_coro,
        client_heartbeat_interval, server_heartbeat_interval,
        connect_timeout=connect_timeout
    )


@click.command()
@click.option('-h', '--host', required=True)
@click.option('-p', '--port', required=True)
@click.option('-U', '--user', required=True)
@click.option('-P', '--password', required=True)
@click.option('-S', '--session', default='', show_default=True)
@click.option('-s', '--sequence', default=1, show_default=True)
@click.option('-t', '--client-heartbeat-interval', default=10, show_default=True)
@click.option('-T', '--server-heartbeat-interval', default=10, show_default=True)
@click.option('-v', '--verbose', count=True)
def tail_messages(host, port, user, password, session, sequence,
                  client_heartbeat_interval, server_heartbeat_interval, verbose):
    utils.enable_logging_tools(verbose)
    asyncio.run(
        soup.tail_soup_app(
            (host, port), user, password, session, sequence, connect_async, client_heartbeat_interval, server_heartbeat_interval
        )
    )


# Enums
class ItchSide(Enum):
    Buy = 'B'
    Sell = 'S'


class SystemEventCode(Enum):
    StartOfMessages = 'O'
    StartOfMarket = 'S'
    EndOfMarket = 'M'
    EndOfMessages = 'C'


class TradingState(Enum):
    Halted = 'H'
    Trading = 'T'
    Paused = 'P'


# Records
# Messages
class SystemEvent(Message, indicator=83, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('timestamp', UnsignedLongBE),
            Field('eventCode', CharIso8599),
        ]

    timestamp: int
    eventCode: SystemEventCode


class StockTradingAction(Message, indicator=72, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('timestamp', UnsignedLongBE),
            Field('stockCode', FixedIsoString(length=10)),
            Field('tradingState', CharIso8599),
        ]

    timestamp: int
    stockCode: str
    tradingState: TradingState


class AddOrder(Message, indicator=65, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('timestamp', UnsignedLongBE),
            Field('orderReferenceNumber', UnsignedLongBE),
            Field('stockCode', FixedIsoString(length=10)),
            Field('side', CharIso8599),
            Field('quantity', UnsignedIntBE),
            Field('price', UnsignedIntBE),
        ]

    timestamp: int
    orderReferenceNumber: int
    stockCode: str
    side: ItchSide
    quantity: int
    price: int


class OrderExecuted(Message, indicator=69, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('timestamp', UnsignedLongBE),
            Field('orderReferenceNumber', UnsignedLongBE),
            Field('executedQuantity', UnsignedIntBE),
            Field('matchNumber', UnsignedLongBE),
        ]

    timestamp: int
    orderReferenceNumber: int
    executedQuantity: int
    matchNumber: int


class OrderCancel(Message, indicator=88, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('timestamp', UnsignedLongBE),
            Field('orderReferenceNumber', UnsignedLongBE),
            Field('canceledQuantity', UnsignedIntBE),
        ]

    timestamp: int
    orderReferenceNumber: int
    canceledQuantity: int


class OrderDelete(Message, indicator=68, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('timestamp', UnsignedLongBE),
            Field('orderReferenceNumber', UnsignedLongBE),
        ]

    timestamp: int
    orderReferenceNumber: int


class Trade(Message, indicator=80, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('timestamp', UnsignedLongBE),
            Field('stockCode', FixedIsoString(length=10)),
            Field('side', CharIso8599),
            Field('quantity', UnsignedIntBE),
            Field('price', UnsignedIntBE),
            Field('matchNumber', UnsignedLongBE),
        ]

    timestamp: int
    stockCode: str
    side: ItchSide
    quantity: int
    price: int
    matchNumber: int



