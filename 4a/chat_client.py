from socket import socket, AF_INET, SOCK_STREAM
import pickle
import time
from sys import argv, exit
import logging
import log.client_log_config

logger = logging.getLogger('client')

def log(func):
    def deco(*args, **kwargs):
        r = func(*args, **kwargs)
        logger.info(f'{func.__name__} running')        
        return r
    return deco

@log
def send_msg(socket, msg_type):    
    socket.send(pickle.dumps(msg_type))

@log
def rcv_msg(socket):    
    server_data = socket.recv(640)
    return pickle.loads(server_data)

def sending_messages(s, account_name):
    while True:
        msg = input('Ваше сообщение (enter "q" to exit) : ')
        if msg == 'q':
            break
        message = {
            "action": "msg",
            "time": time.time(),
            "to": "#room_name",
            "from": account_name,
            "message": msg
        }
        send_msg(s, message)    # Отправить!

def reading_messages(s):
    while True:
        data = pickle.loads(s.recv(640))
        print(f'От: {data["from"]} сообщение: --{data["message"]}--')

@log
def communication(s, name):
    role = ''  # выбор работы клиента в качестве отправителя либо получателя сообщений
    while role != 's' and role !='r':
        role = input('Выберите роль - отправитель(s) / получатель(r) : ')
    if role == 's':
        sending_messages(s, name)
    else:
        reading_messages(s)


def main():
    try:
        addr = argv[1]
    except IndexError:
        logger.error("attempt to start without specifying the server")
        exit('Необходимо указать IP-адрес сервера')
    port = int(argv[2]) if len(argv) > 2 else 7777

    s = socket(AF_INET, SOCK_STREAM)
    s.connect((addr, port))

    account_name = "C0deMaver1ck"

    presence = {
        "action": "presence",
        "time": time.time(),
        "type": "status",
        "user": {
            "account_name": account_name,
            "status": "Yep, I am here!"
        }
    }
    send_msg(s, presence)

    server_msg = rcv_msg(s)
    if server_msg['response']:
        logger.info("%(alert)s with code %(response)s", server_msg)

    communication(s, account_name)    # основная функция чата

    s.close()

            
if __name__ == '__main__':

    main()
