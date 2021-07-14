from socket import socket, AF_INET, SOCK_STREAM
import pickle
import time
from sys import argv, exit
import logging
import log.client_log_config
from threading import Thread

logger = logging.getLogger('client')


def log(func):
    def deco(*args, **kwargs):
        r = func(*args, **kwargs)
        logger.info(f'{func.__name__} running')
        return r
    return deco


class ClientMeta(type):
    def __init__(self, clsname, bases, clsdict):
        # pass
        for key, value in clsdict.items():
            # Пропустить специальные и частные методы
            if key.startswith("__"):
                continue

            # Пропустить любые невызываемые объекты
            if not hasattr(value, "__call__"):
                continue

            # Проверить отсутствие вызовов accept  для сокетов
            if getattr(value, "accept"):
                raise TypeError("class %s must not call accept" % clsname)

            # Проверить отсутствие вызовов listen для сокетов
            if getattr(value, "listen"):
                raise TypeError("class %s must not call listen" % clsname)

            # Проверить отсутствие создания сокетов на уровне классов
            if getattr(value, "socket"):
                raise TypeError("class %s must have not a socket" % clsname)


class ClientVerifier(metaclass=ClientMeta):
    pass


class PortVerifier:

    def __init__(self):
        self._value = 0

    def __get__(self, instance, instance_type):
        return self._value

    def __set(self, instance, value):
        if value < 0:
            raise ValueError("Оценка должна быть от 1 до 5")
        self._value = value


class Client(ClientVerifier):

    def __init__(self):
        try:
            self.addr = argv[1]
        except IndexError:
            logger.error("attempt to start without specifying the server")
            exit('Необходимо указать IP-адрес сервера')
        # self.port = int(argv[2]) if len(argv) > 2 else 7777
        try:
            self.port = PortVerifier(int(argv[2]))
        except IndexError:
            self.port = PortVerifier(7777)

        self.account_name = input("Введите имя(ник): ") or "guest_user"
        print("__dict__:", Client.__dict__)

    @log
    def send_msg(self, socket, msg_type):
        socket.send(pickle.dumps(msg_type))

    @log
    def rcv_msg(self, socket):
        server_data = socket.recv(640)
        return pickle.loads(server_data)

    def sending_messages(self, s, account_name):
        interlocutor = input('Введите имя собеседника : ')

        while True:
            msg = input('Ваше сообщение (enter "q" to exit) : ')
            if msg == 'q':
                message = {
                    "action": "quit",
                }
                self.send_msg(s, message)
                break
            message = {
                "action": "msg",
                "time": time.time(),
                "to": interlocutor,
                "from": account_name,
                "message": msg
            }
            self.send_msg(s, message)    # Отправить!

    def sending_group_messages(self, s, account_name):
        group = input('Введите номер группы (начиная с #) : ')
        join_msg = {
            "action": "join",
            "time": time.time(),
            "room": group
        }
        self.send_msg(s, join_msg)

        while True:
            msg = input('Ваше сообщение (enter "q" to exit) : ')
            if msg == 'q':
                message = {
                    "action": "quit",
                }
                self.send_msg(s, message)
                break
            message = {
                "action": "msg",
                "time": time.time(),
                "to": group,
                "from": account_name,
                "message": msg
            }
            self.send_msg(s, message)    # Отправить!

    def reading_messages(self, s):
        while True:
            data = pickle.loads(s.recv(640))
            # if data['action'] == 'msg':
            if 'action' in data.keys():
                print(f'\n    {data["from"]}: " {data["message"]} "')
            if 'response' in data.keys():
                print(f'\n    {data["alert"]}')

    def presence_msg_send(self, s, nik):
        presence = {
            "action": "presence",
            "time": time.time(),
            "type": "status",
            "user": {
                "account_name": nik,
                "status": "Yep, I am here!"
            }
        }
        self.send_msg(s, presence)
        return

    @log
    def communication(self, s, name):
        while True:
            action_choice = ''
            while action_choice != 's' and action_choice != 'g' and action_choice != 'q':
                action_choice = input(
                    '\u2193\u2193\u2193 Введите желаемое действие \u2193\u2193\u2193\n сообщение пользователю (s), \n сообщение группе     (g), \n покинуть программу    (q)? : ')

            if action_choice == 's':
                self.sending_messages(s, name)
            elif action_choice == 'g':
                self.sending_group_messages(s, name)
            if action_choice == 'q':
                break
        return


if __name__ == '__main__':

    c = Client()

    c.s = socket(AF_INET, SOCK_STREAM)
    print(c.s.__dict__)
    c.s.connect((c.addr, c.port))
    c.presence_msg_send(c.s, c.account_name)
    c.server_msg = c.rcv_msg(c.s)
    if c.server_msg['response']:
        print(f'Добро пожаловать в чат, {c.account_name}')
        logger.info("%(alert)s with code %(response)s", c.server_msg)

    t = Thread(target=c.reading_messages, args=(c.s, ))
    t.daemon = True
    t.start()

    c.communication(c.s, c.account_name)    # основная функция чата
    c.s.close()
