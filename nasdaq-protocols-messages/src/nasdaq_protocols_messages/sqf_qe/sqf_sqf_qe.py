import asyncio
from enum import Enum
from typing import Callable, Awaitable, Type

import click
from nasdaq_protocols.common import utils
from nasdaq_protocols.common import logable
from nasdaq_protocols.common.message import *
from nasdaq_protocols import soup, sqf


__all__ = [
    'Message',
    'ClientSession',
    'connect_async',
    'tail_messages',
    'QuoteState',
    'RejectReason',
    'EnterQuote',
    'PurgeQuotes',
    'QuoteAccepted',
    'QuoteRejected',
    'QuoteExecuted',
]


@logable
class Message(sqf.Message, app_name='sqf_qe'):
    def __init_subclass__(cls, **kwargs):
        cls.log.debug('subclassing %s, params = %s', cls.__name__, str(kwargs))
        if 'indicator' not in kwargs:
            raise ValueError('expected "indicator" when subclassing sqf_qe.Message')

        kwargs['app_name'] = 'sqf_qe'
        super().__init_subclass__(**kwargs)


class ClientSession(sqf.ClientSession):
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

    return await sqf.connect_async(
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
class QuoteState(Enum):
    Live = 'L'
    Dead = 'D'


class RejectReason(Enum):
    InvalidPrice = 'P'
    InvalidQuantity = 'Q'
    ClosedMarket = 'C'


# Records
# Messages
class EnterQuote(Message, indicator=81, direction='incoming'):
    class BodyRecord(Record):
        Fields = [
            Field('token', LongBE),
            Field('stockCode', FixedIsoString(length=10)),
            Field('bidPrice', UnsignedIntBE),
            Field('bidQuantity', UnsignedIntBE),
            Field('askPrice', UnsignedIntBE),
            Field('askQuantity', UnsignedIntBE),
            Field('account', FixedIsoString(length=16)),
        ]

    token: int
    stockCode: str
    bidPrice: int
    bidQuantity: int
    askPrice: int
    askQuantity: int
    account: str


class PurgeQuotes(Message, indicator=80, direction='incoming'):
    class BodyRecord(Record):
        Fields = [
            Field('token', LongBE),
            Field('stockCode', FixedIsoString(length=10)),
        ]

    token: int
    stockCode: str


class QuoteAccepted(Message, indicator=65, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('token', LongBE),
            Field('stockCode', FixedIsoString(length=10)),
            Field('bidPrice', UnsignedIntBE),
            Field('bidQuantity', UnsignedIntBE),
            Field('askPrice', UnsignedIntBE),
            Field('askQuantity', UnsignedIntBE),
            Field('quoteState', CharIso8599),
        ]

    token: int
    stockCode: str
    bidPrice: int
    bidQuantity: int
    askPrice: int
    askQuantity: int
    quoteState: QuoteState


class QuoteRejected(Message, indicator=74, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('token', LongBE),
            Field('reason', CharIso8599),
        ]

    token: int
    reason: RejectReason


class QuoteExecuted(Message, indicator=69, direction='outgoing'):
    class BodyRecord(Record):
        Fields = [
            Field('token', LongBE),
            Field('executedQuantity', UnsignedIntBE),
            Field('executionPrice', UnsignedIntBE),
            Field('matchNumber', UnsignedLongBE),
        ]

    token: int
    executedQuantity: int
    executionPrice: int
    matchNumber: int



