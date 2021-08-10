import functools
import hmac
import logging
import pickle
import time
from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM
from sys import argv, exit
from threading import Thread

from PyQt5 import QtCore, QtWidgets
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import or_
from sqlalchemy.sql.sqltypes import DateTime

import chat_client_ui


def client_authenticate(connection, secret_key):
    """ Аутентификация клиента на удаленном сервисе.
    Параметр connection - сетевое соединение (сокет);
    secret_key - ключ шифрования, известный клиенту и серверу
    """
    message = connection.recv(32)
    hash_ = hmac.new(secret_key, message, 'sha1')
    digest = hash_.digest()
    connection.send(digest)


secret_key = b'our_secret_key'

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


def login_required(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        if c.account_name == "guest_user":
            raise Exception("требуется авторизация")
        else:
            return func(*args, **kwargs)

    return wrap


@login_required
def some_function():
    print("somedata")


class Client:

    def __init__(self):
        try:
            self.addr = argv[1]
        except IndexError:
            logger.error("attempt to start without specifying the server")
            exit('Необходимо указать IP-адрес сервера')
        self.port = int(argv[2]) if len(argv) > 2 else 7777

        self.account_name = input("Введите имя(ник): ") or "guest_user"
        if self.account_name != "guest_user":
            self.passwd = input("Введите пароль: ")
        else:
            self.passwd = ''
        self.interlocutor = ''

    @log
    def send_msg(self, socket, msg_type):
        socket.send(pickle.dumps(msg_type))

    @log
    def rcv_msg(self, socket):
        server_data = socket.recv(640)
        return pickle.loads(server_data)

    def sending_messages(self, s, account_name):
        """Режим личных сообщений. Задействуется только в консольном режиме"""
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
            self.send_msg(s, message)

            new_msg = MsgHistory(self.account_name, interlocutor, msg)
            session.add(new_msg)
            session.commit()

    def sending_group_messages(self, s, account_name):
        """Режим групповых сообщений. Задействуется только в консольном режиме"""
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
            self.send_msg(s, message)

    def reading_messages(self, s):
        """Приём сообщений. Запускается в отдельном потоке"""
        r_session = Session()
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
                    r_session.add(new_msg)
                    r_session.commit()

            if 'response' in data.keys():
                print(f'\n    {data["alert"]}')

    def presence_msg_send(self, s):
        """Отправить серверу п"""
        presence = {
            "action": "presence",
            "time": time.time(),
            "type": "status",
            "user": {
                "account_name": self.account_name,
                "status": "Yep, I am here!",
                "password": self.passwd
            }
        }
        self.send_msg(s, presence)
        return

    def clients_request(self, s):
        cls_request = {
            "action": "get_contacts",
            "time": time.time(),
            "user_login": self.account_name
        }
        self.send_msg(s, cls_request)
        return

    @log
    def communication(self, s, name):
        """Организовать поочерёдный запуск бесед по запросу пользователя. Только в консольном режиме"""
        while True:
            action_choice = ''
            while action_choice != 's' and action_choice != 'g' and action_choice != 'q':
                action_choice = input(
                    '\u2193\u2193\u2193 Введите желаемое действие \u2193\u2193\u2193\n сообщение пользователю (s), '
                    '\n сообщение группе     (g), \n покинуть программу    (q)? : ')

            if action_choice == 's':
                self.sending_messages(s, name)
            elif action_choice == 'g':
                self.sending_group_messages(s, name)
            if action_choice == 'q':
                break
        return

    def change_chat(self, item):
        """Сменить беседу по запросу пользователя. Только в графическом режиме"""
        self.interlocutor = item.text()
        chat_view = session.query(MsgHistory.time, MsgHistory.origin, MsgHistory.consumer, MsgHistory.message).filter(
            or_(
                MsgHistory.origin == self.interlocutor, MsgHistory.consumer == self.interlocutor)).all()
        chat_view = [str(repl[0])[5:16] + ':\t' + repl[1] + ' -> ' +
                     repl[2] + ':\t' + repl[3] for repl in chat_view]
        talk_model = QtCore.QStringListModel()
        talk_model.setStringList(chat_view)
        ui.listView_talk.setModel(talk_model)

    # @login_required
    def add_contact(self):
        """Добавить собеседника по запросу пользователя. Только в графическом режиме"""
        new_contact = Contact(ui.lineEdit.text())
        session.add(new_contact)
        session.commit()
        new_list = session.query(Contact.companion).all()
        ui.listView_chats.clear()
        for contact in new_list:
            ui.listView_chats.addItem(contact[0])
        ui.lineEdit.clear()

    def qt_send_msg(self, s):
        """Организовать отправку сообщения в графическом режиме"""
        msg = ui.textEdit.toPlainText()
        message = {
            "action": "msg",
            "time": time.time(),
            "to": self.interlocutor,
            "from": self.account_name,
            "message": msg
        }
        new_msg = MsgHistory(self.account_name, self.interlocutor, msg)
        session.add(new_msg)
        session.commit()
        self.s.send(pickle.dumps(message))

        chat_view = session.query(MsgHistory.time, MsgHistory.origin, MsgHistory.consumer, MsgHistory.message).filter(
            or_(
                MsgHistory.origin == self.interlocutor, MsgHistory.consumer == self.interlocutor)).all()
        chat_view = [str(repl[0])[5:16] + ':\t' + repl[1] + ' -> ' +
                     repl[2] + ':\t' + repl[3] for repl in chat_view]
        talk_model = QtCore.QStringListModel()
        talk_model.setStringList(chat_view)
        ui.listView_talk.setModel(talk_model)
        ui.textEdit.clear()


if __name__ == '__main__':

    c = Client()

    c.s = socket(AF_INET, SOCK_STREAM)
    c.s.connect((c.addr, c.port))

    client_authenticate(c.s, secret_key)
    c.presence_msg_send(c.s)
    c.server_msg = c.rcv_msg(c.s)
    if c.server_msg['response'] == 202:
        print(f'Добро пожаловать в чат, {c.account_name}')
        logger.info("%(alert)s with code %(response)s", c.server_msg)
    elif c.server_msg['response'] == 402:
        print(f'{c.account_name}, ваш пароль или логин неверен')
        logger.info("%(alert)s with code %(response)s", c.server_msg)
        exit()

    app = QtWidgets.QApplication(argv)
    window = QtWidgets.QMainWindow()
    ui = chat_client_ui.Ui_MainWindow()
    ui.setupUi(window, c.account_name)
    window.show()

    c.clients_request(c.s)
    c.chats_list = c.rcv_msg(c.s)
    if c.chats_list['response']:
        print(f'Список ваших контактов: {c.chats_list["alert"]}')

    ui.listView_chats.addItems(c.chats_list["alert"])
    ui.listView_chats.itemDoubleClicked.connect(c.change_chat)
    ui.addButton.clicked.connect(c.add_contact)
    ui.sendButton.clicked.connect(c.qt_send_msg)

    engine = create_engine(f'sqlite:///client_{c.account_name}_entries.sqlite')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    t = Thread(target=c.reading_messages, args=(c.s,))
    t.daemon = True
    t.start()

    c.communication(c.s, c.account_name)  # основная функция чата
    c.s.close()

    exit(app.exec_())
