import hmac
import logging
import os
import pickle
import select
import time
from argparse import ArgumentParser
from datetime import datetime
from hashlib import pbkdf2_hmac
from socket import socket, AF_INET, SOCK_STREAM
from sys import argv, exit

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import DateTime

engine = create_engine('sqlite:///server_storage.sqlite')
Session = sessionmaker(bind=engine)


def server_authenticate(connection, secret_key):
    """ Запрос аутентификаии клиента.
    connection - сетевое соединение (сокет);
    secret_key - ключ шифрования, известный клиенту и серверу
    """
    # 1. Создаётся случайное послание и отсылается клиенту
    message = os.urandom(32)
    connection.send(message)

    # 2. Вычисляется HMAC-функция от послания с использованием секретного ключа
    hash = hmac.new(secret_key, message, 'sha1')
    digest = hash.digest()

    # 3. Пришедший ответ от клиента сравнивается с локальным результатом HMAC
    response = connection.recv(len(digest))
    return hmac.compare_digest(digest, response)


secret_key = b'our_secret_key'

Storage = declarative_base()


def hsh(password):
    """Вычислить хэш пароля пользователя"""
    return pbkdf2_hmac('sha256', password.encode(
        'utf-8'), b'saltsaltsaltsalt', 100000)


class Client(Storage):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    login = Column(String)
    password = Column(String)
    info = Column(String)

    def __init__(self, name, passwd):
        self.login = name
        self.password = hsh(passwd)

    def __repr__(self):
        return "<Client ('%s')>" % self.login


class ClientHistory(Storage):
    __tablename__ = 'clients_history'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    entry_time = Column(DateTime)
    ip_addr = Column(String)

    def __init__(self, client, IP) -> None:
        self.client_id = client
        self.ip_addr = IP
        self.entry_time = datetime.now()

    def __repr__(self):
        return "<Client ('%s') connected at ('%s') from ('%s')>" % (self.client_id, self.entry_time, self.ip_addr)


class ClientContact(Storage):
    __tablename__ = 'client_contacts'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    interlocutor = Column(Integer, ForeignKey('clients.id'))

    def __init__(self, client, interlocutor) -> None:
        self.client_id = client
        self.interlocutor = interlocutor

    def __repr__(self):
        return "<Client ('%s') contact with ('%s')>" % (self.client_id, self.interlocutor)


Storage.metadata.create_all(engine)

logger = logging.getLogger('server_app')


def log(func):
    def deco(*args, **kwargs):
        logger.info(f'function "{func.__name__}"" running')
        r = func(*args, **kwargs)
        return r

    return deco


class Server:
    """Здесь весь сервер"""

    def __init__(self):

        self.interlocutors = {}
        self.groups = {}

        self.arg = self.create_parser().parse_args(argv[1:])
        self.s = self.new_listen_socket()
        self.clients = []

        while True:
            try:
                conn, addr = self.s.accept()  # Проверка подключений
                if not server_authenticate(conn, secret_key):
                    conn.close()
            except OSError as e:
                pass  # timeout вышел
            else:
                print(f'Получен запрос на соединение с {str(addr)}')
                self.clients.append(conn)
            finally:
                # Проверить наличие событий ввода-вывода без таймаута
                wait = 3
                self.r = []
                self.w = []
                try:
                    self.r, self.w, e = select.select(
                        self.clients, self.clients, [], wait)
                except KeyboardInterrupt:
                    print("-Сервер остановлен")
                    exit()
                except Exception as e:
                    # Исключение произойдет, если какой-то клиент отключится
                    pass  # Ничего не делать, если какой-то клиент отключился

                self.requests = self.read_requests()  # Сохраним запросы клиентов
                if self.requests:
                    # Выполним отправку ответов клиентам
                    # self.write_responses(self.requests, self.w, self.clients)
                    self.write_responses()

    @log
    def new_listen_socket(self):
        """Установить соединение с клиентом"""
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind((self.arg.address, int(self.arg.port)))
        sock.listen(5)
        sock.settimeout(0.2)
        return sock

    @log
    def create_parser(self):
        parser = ArgumentParser()
        parser.add_argument('-p', '--port', default=7777)
        parser.add_argument('-a', '--address', default='')
        return parser

    def read_requests(self):
        """ Чтение запросов из списка клиентов"""
        self.requests = {}  # Словарь запросов клиентов вида {сокет: запрос}

        for sock in self.r:
            try:
                self.requests[sock] = pickle.loads(sock.recv(640))
            except Exception:
                print('Клиент {} {} отключился'.format(
                    sock.fileno(), sock.getpeername()))
                self.clients.remove(sock)
        return self.requests

    @log
    def write_responses(self):
        """ Эхо-ответ сервера клиентам, от которых были запросы"""

        for sock in self.w:
            if sock in self.requests:
                try:
                    # Подготовить и отправить ответ сервера
                    if self.requests[sock]['action'] == 'presence':
                        self.interlocutors[self.requests[sock]
                                           ['user']['account_name']] = sock

                        logger.info(
                            f'presence message received from client {sock.getpeername()}')

                        presence_name = self.requests[sock]['user']['account_name']
                        presence_pass = self.requests[sock]['user']['password']

                        check_client = session.query(Client.login).filter(
                            Client.login == presence_name).all()
                        response = {
                            "response": None,
                            "time": time.time(),
                            "alert": ''
                        }
                        if not check_client:  # новый клиент - добавить в базу
                            new_cl = Client(
                                presence_name, presence_pass)
                            session.add(new_cl)
                            session.commit()
                            response["response"] = 202
                            response["alert"] = "chat-server confirm connection"
                        else:  # клиент в базе - сверить пароль!
                            bd_pass = session.query(Client.password).filter(
                                Client.login == presence_name).all()[0][0]
                            if bd_pass != hsh(presence_pass):
                                response["response"] = 402
                                response["alert"] = "wrong login / password!"
                            else:
                                response["response"] = 202
                                response["alert"] = "chat-server confirm connection"
                        sock.send(pickle.dumps(response))

                        new_cl_id = session.query(Client.id).filter(
                            Client.login == presence_name).one()
                        cl_hist = ClientHistory(
                            new_cl_id[0], sock.getpeername()[0])
                        session.add(cl_hist)
                        session.commit()

                    # Выдать список клиентов
                    elif self.requests[sock]['action'] == 'get_contacts':
                        login = self.requests[sock]['user_login']
                        login_id = session.query(Client.id).filter(
                            Client.login == login).one()[0]
                        contact_sample = session.query(ClientContact.interlocutor).filter(
                            ClientContact.client_id == login_id).all()
                        contact_sample.extend(session.query(ClientContact.client_id).filter(
                            ClientContact.interlocutor == login_id).all())
                        contact_ids = set(map(lambda x: x[0], contact_sample))
                        contact_list = []
                        for cnt_id in contact_ids:
                            contact_list.append(session.query(Client.login).filter(
                                Client.id == cnt_id).first()[0])
                        response = {
                            "response": 202,
                            "alert": contact_list
                        }
                        sock.send(pickle.dumps(response))

                except Exception as e:  # Сокет недоступен, клиент отключился
                    print(e)
                    print('Клиент {} {} отключился'.format(
                        sock.fileno(), sock.getpeername()))
                    sock.close()
                    self.clients.remove(sock)

        for sock in self.requests:

            if self.requests[sock]['action'] == 'msg':
                response = self.requests[sock]
                msg_copy = self.requests[sock]['message']
                logger.info(
                    f'text message "{msg_copy}" received from client {sock.getpeername()}')

                if self.requests[sock]['to'].startswith('#'):
                    for group_member in self.groups[self.requests[sock]['to']]:
                        if group_member != sock:
                            try:
                                group_member.send(pickle.dumps(response))
                            except Exception as e:
                                pass
                else:
                    try:
                        self.interlocutors[self.requests[sock]['to']].send(
                            pickle.dumps(response))

                        id_from = session.query(Client.id).filter(
                            Client.login == self.requests[sock]['from']).one()[0]
                        id_to = session.query(Client.id).filter(
                            Client.login == self.requests[sock]['to']).one()[0]
                        new_interlocution = ClientContact(id_from, id_to)
                        session.add(new_interlocution)
                        session.commit()

                    except KeyError:
                        print("неудачная отправка сообщения отсутствующему абоненту")

            elif self.requests[sock]['action'] == 'quit':
                print(
                    f'<{self.requests[sock]["from"]}> покинул беседу с <{self.requests[sock]["to"]}>')
                # del interlocutors[requests[sock]]

            elif self.requests[sock]['action'] == 'join':
                if self.requests[sock]['room'] not in self.groups:
                    self.groups[self.requests[sock]['room']] = [sock, ]
                    response = {
                        "response": 100,
                        "alert": f'Группа найдена не была. Группа {self.requests[sock]["room"]} создана'
                    }
                    sock.send(pickle.dumps(response))
                else:
                    self.groups[self.requests[sock]['room']].append(sock)
                print(
                    f'joining <{self.requests[sock]["from"]}> to group : {self.requests[sock]["room"]}')


if __name__ == '__main__':
    session = Session()
    srv = Server()
