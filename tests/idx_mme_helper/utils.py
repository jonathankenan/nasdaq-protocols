import logging, string, random, os
from nasdaq_mme_idx import fix_oe_50
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)

# Login FIX

async def loginFIX(hostname, port):
    login_msg: fix_oe_50.Logon = fix_oe_50.Logon()
    login_msg.Header.MsgSeqNum = 1
    login_msg.EncryptMethod = fix_oe_50.EncryptMethod.None_
    login_msg.EncryptMethod = 0
    login_msg.HeartBtInt = 10
    login_msg.Username = 'XXJFE1'
    login_msg.Password = 'P@ssw0rd!1'
    login_msg.ResetSeqNumFlag = True
    login_msg.Header.SenderCompID = 'XX'
    login_msg.Header.SenderSubID = 'XXJFE1'
    login_msg.Header.TargetCompID = 'MME'
    login_msg.Header.MsgSeqNum = 1
    login_msg.DefaultApplVerID = fix_oe_50.DefaultApplVerID.FIX50SP2
    fix_session = await fix_oe_50.connect_async((hostname, port), login_msg, client_heartbeat_interval=1,
    server_heartbeat_interval=10)

    return fix_session

async def loginFIXFromFile(hostname, port, username, password, senderCompID):
    try:
        login_msg: fix_oe_50.Logon = fix_oe_50.Logon()
        login_msg.Header.MsgSeqNum = 1
        login_msg.EncryptMethod = fix_oe_50.EncryptMethod.None_
        login_msg.HeartBtInt = 10
        login_msg.Username = username
        login_msg.Password = password
        login_msg.ResetSeqNumFlag = True
        login_msg.Header.SenderCompID = senderCompID
        login_msg.Header.SenderSubID = username
        login_msg.Header.TargetCompID = 'MME'
        login_msg.DefaultApplVerID = fix_oe_50.DefaultApplVerID.FIX50SP2

        fix_session = await fix_oe_50.connect_async(
            (hostname, port),
            login_msg,
            client_heartbeat_interval=1,
            server_heartbeat_interval=30
        )

        logging.info(f"User {username} connected successfully")
        return fix_session
    except Exception as e:
        logging.error(f"Error during login for {username}: {e}")
        return None
    
async def loginFIXFromFile1(hostname, port, username, password, senderCompID, msgSeqNum=1):
    try:
        login_msg: fix_oe_50.Logon = fix_oe_50.Logon()

        # 🔥 PENTING: pakai parameter, bukan hardcode
        login_msg.Header.MsgSeqNum = msgSeqNum

        login_msg.EncryptMethod = fix_oe_50.EncryptMethod.None_
        login_msg.HeartBtInt = 10
        login_msg.Username = username
        login_msg.Password = password

        login_msg.ResetSeqNumFlag = False

        login_msg.Header.SenderCompID = senderCompID
        login_msg.Header.SenderSubID = username
        login_msg.Header.TargetCompID = 'MME'

        login_msg.DefaultApplVerID = fix_oe_50.DefaultApplVerID.FIX50SP2

        fix_session = await fix_oe_50.connect_async(
            (hostname, port),
            login_msg,
            client_heartbeat_interval=1,
            server_heartbeat_interval=30
        )

        logging.info(f"User {username} connected successfully (seq={msgSeqNum})")
        return fix_session

    except Exception as e:
        logging.error(f"Error during login for {username} (seq={msgSeqNum}): {e}")
        return None    

def format_fix(msg):
    raw = str(msg)
    return raw.replace("\x01", "|")


async def on_fix_message(session, msg):
    logging.info(f"<<< IN  {format_fix(msg)}")


async def INETloginFIXFromFile(hostname, port, username, password, senderCompID, reset_seq=True, last_seq=None):
    try:
        login_msg: fix_oe_50.Logon = fix_oe_50.Logon()

        # Atur MsgSeqNum
        if reset_seq:
            login_msg.Header.MsgSeqNum = 1
            login_msg.ResetSeqNumFlag = True
        else:
            login_msg.Header.MsgSeqNum = last_seq if last_seq else 1
            login_msg.ResetSeqNumFlag = False

        # Session info
        login_msg.EncryptMethod = fix_oe_50.EncryptMethod.None_
        login_msg.HeartBtInt = 10
        login_msg.Username = username
        login_msg.Password = password
        login_msg.Header.SenderCompID = senderCompID
        login_msg.Header.SenderSubID = username
        login_msg.Header.TargetCompID = 'IDX'
        login_msg.DefaultApplVerID = fix_oe_50.DefaultApplVerID.FIX50SP1

        # 🔹 LOG OUTGOING MESSAGE
        logging.info(f">>> OUT {format_fix(login_msg)}")

        # Connect dengan callback
        fix_session = await fix_oe_50.connect_async(
            (hostname, port),
            login_msg,
            on_msg_coro=on_fix_message,
            client_heartbeat_interval=10,
            server_heartbeat_interval=30
        )

        logging.info(f"User {username} connected successfully")
        return fix_session

    except Exception as e:
        logging.error(f"Error during login for {username}: {e}")
        return None

#Load any data from file
    
def load_credentials(file_path):
    with open(file_path, 'r') as f:
        credentials = []
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 4:
                continue

            user, password, order_count, sender_comp_id = parts[:4]
            duration_minutes = float(parts[4]) if len(parts) >= 5 else 2  # default 2 menit

            credentials.append({
                'username': user,
                'password': password,
                'order_count': int(order_count),
                'sender_comp_id': sender_comp_id,
                'duration_minutes': duration_minutes
            })
    return credentials

def load_orders(file_path):
    with open(file_path, 'r') as f:
        orders = []
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split('|')
            if len(parts) < 4:
                continue

            symbol_id = parts[0]
            price = float(parts[1])
            side = parts[2]
            qty = float(parts[3])
            otype = parts[4].strip().upper() if len(parts) >= 5 else 'L'

            if otype.startswith('M'):
                ord_type = fix_oe_50.OrdType.Market
            elif otype.startswith('L'):
                ord_type = fix_oe_50.OrdType.Limit

            orders.append({
                'Symbol': symbol_id,
                'Price': price,
                'Side': side,
                'OrderQty': qty,
                'OrderType': ord_type
            })

            # logging.info(f"Loaded order: {symbol_id} | {price} | {side} | {qty} | type={otype}")

    return orders

# Logging

def setup_logging():
    log_dir = "log"
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"orders_{now}.log")

    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
    logging.info(f"Logging started — file: {log_file}")
    return log_file

def ouch_setup_logging():
    log_dir = "conn_logs"
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"OUCH_conn_{now}.log")

    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
    logging.info(f"Logging started — file: {log_file}")
    return log_file

def fix_setup_logging():
    log_dir = "conn_logs"
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"FIX5_conn_{now}.log")

    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
    logging.info(f"Logging started — file: {log_file}")
    return log_file

def itch_setup_logging():
    log_dir = "conn_logs"
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"ITCH_conn_{now}.log")

    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
    logging.info(f"Logging started — file: {log_file}")
    return log_file

# Others

# Random number return
def generate_ordertoken():
    return ''.join(random.choice(string.digits) for _ in range(8))

# Random string return
def generate_ordertoken1():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))

def get_time():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H:%M:%S")