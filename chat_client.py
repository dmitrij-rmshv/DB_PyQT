from socket import socket, AF_INET, SOCK_STREAM
import pickle
import time
from sys import argv, exit
import logging
import log.client_log_config
from threading import Thread
from sqlalchemy import create_engine, engine
from sqlalchemy import Table, Column, Integer, Numeric, String, MetaData, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from sqlalchemy.sql.functions import now
from sqlalchemy.sql.sqltypes import DateTime


Base = declarative_base()


class Contact(Base):
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    companion = Column(String)

    def __init__(self, name):
        self.companion = name

    def __repr__(self):
        return "<Companion ('%s')>" % self.companion


class MsgHistory(Base):
    __tablename__ = 'stories'
    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    origin = Column(String, ForeignKey('contacts.companion'))
    consumer = Column(String, ForeignKey('contacts.companion'))
    # origin = Column(String)
    # consumer = Column(String)
    message = Column(String)

    def __init__(self, from_, to, msg):
        self.time = datetime.now()
        self.origin = from_
        self.consumer = to
        self.message = msg

    def __repr__(self):
        return "< ('%s') -> ('%s') : ('%s') at ('%s') >" % (self.origin, self.consumer, self.message, self.time)


logger = logging.getLogger('client')


def log(func):
    def deco(*args, **kwargs):
        r = func(*args, **kwargs)
        logger.info(f'{func.__name__} running')
        return r
    return deco


class Client:

    def __init__(self):
        try:
            self.addr = argv[1]
        except IndexError:
            logger.error("attempt to start without specifying the server")
            exit('Необходимо указать IP-адрес сервера')
        self.port = int(argv[2]) if len(argv) > 2 else 7777

        self.account_name = input("Введите имя(ник): ") or "guest_user"

    @ log
    def send_msg(self, socket, msg_type):
        socket.send(pickle.dumps(msg_type))

    @ log
    def rcv_msg(self, socket):
        server_data = socket.recv(640)
        return pickle.loads(server_data)

    def sending_messages(self, s, account_name):
        interlocutor = input('Введите имя собеседника : ')

        new_contact = Contact(interlocutor)
        session.add(new_contact)
        session.commit()

        while True:
            msg = input(f'Ваше сообщение для {interlocutor} ("q" to exit) : ')
            if msg == 'q':
                message = {
                    "action": "quit",
                    "to": interlocutor,
                    "from": account_name
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

            new_msg = MsgHistory(self.account_name, interlocutor, msg)
            session.add(new_msg)
            session.commit()

    def sending_group_messages(self, s, account_name):
        group = input('Введите номер группы (начиная с #) : ')
        join_msg = {
            "action": "join",
            "time": time.time(),
            "room": group,
            "from": account_name
        }
        self.send_msg(s, join_msg)

        while True:
            msg = input(
                f'Ваше сообщение в группу {group} ("q" to exit) : ')
            if msg == 'q':
                message = {
                    "action": "quit",
                    "to": group,
                    "from": account_name
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
                if data['to'].startswith('#'):
                    print(
                        f'\n    <{data["from"]}> to group <{data["to"]}>: " {data["message"]} "')
                else:
                    print(f'\n    <{data["from"]}>: " {data["message"]} "')

                    new_msg = MsgHistory(
                        data['from'], data['to'], data['message'])
                    session.add(new_msg)
                    session.commit()

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

    def clients_request(self, s):
        cls_rqst = {
            "action": "get_contacts",
            "time": time.time(),
            "user_login": self.account_name
        }
        self.send_msg(s, cls_rqst)
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
    c.s.connect((c.addr, c.port))
    c.presence_msg_send(c.s, c.account_name)
    c.server_msg = c.rcv_msg(c.s)
    if c.server_msg['response']:
        print(f'Добро пожаловать в чат, {c.account_name}')
        logger.info("%(alert)s with code %(response)s", c.server_msg)
    c.clients_request(c.s)
    c.chats_list = c.rcv_msg(c.s)
    if c.chats_list['response']:
        print(f'Список ваших контактов: {c.chats_list["alert"]}')

    engine = create_engine(f'sqlite:///client_{c.account_name}_entries.sqlite')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    t = Thread(target=c.reading_messages, args=(c.s, ))
    t.daemon = True
    t.start()

    c.communication(c.s, c.account_name)    # основная функция чата
    c.s.close()
