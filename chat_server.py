from socket import socket, AF_INET, SOCK_STREAM
import time
import pickle
from sys import argv
from argparse import ArgumentParser
import logging
import select
import dis
import inspect

import log.server_log_config

logger = logging.getLogger('server_app')


def log(func):
    def deco(*args, **kwargs):
        logger.info(f'function "{func.__name__}"" running')
        r = func(*args, **kwargs)
        return r
    return deco


def find_forbidden_methods_call(func, method_names):
    for instr in dis.get_instructions(func):
        if instr.opname == 'LOAD_METHOD' and instr.argval in method_names:
            return instr.argval


class ServerMeta(type):

    forbidden_method_names = ('connect', )

    def __new__(cls, name, bases, class_dict):
        for _, value in class_dict.items():
            if inspect.isfunction(value):
                method_name = find_forbidden_methods_call(
                    value, cls.forbidden_method_names)
                if method_name:
                    raise ValueError(
                        f'called forbidden method "{method_name}"')
        return type.__new__(cls, name, bases, class_dict)


class ServerVerifier(metaclass=ServerMeta):
    pass


class Server(ServerVerifier):

    def __init__(self):

        self.interlocutors = {}
        self.groups = {}

        self.arg = self.create_parser().parse_args(argv[1:])
        self.s = self.new_listen_socket()
        self.clients = []

        while True:
            try:
                conn, addr = self.s.accept()  # Проверка подключений
            except OSError as e:
                pass                        # timeout вышел
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
                except Exception as e:
                    # Исключение произойдет, если какой-то клиент отключится
                    pass        # Ничего не делать, если какой-то клиент отключился

                self.requests = self.read_requests()  # Сохраним запросы клиентов
                if self.requests:
                    # Выполним отправку ответов клиентам
                    # self.write_responses(self.requests, self.w, self.clients)
                    self.write_responses()

    @log
    def new_listen_socket(self):
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
        """ Чтение запросов из списка клиентов
        """
        self.requests = {}  # Словарь запросов клиентов вида {сокет: запрос}

        for sock in self.r:
            try:
                self.requests[sock] = pickle.loads(sock.recv(640))
            except:
                # print('Клиент {} {} отключился'.format(sock.fileno(), sock.getpeername()))
                print('Клиент  отключился')
                self.clients.remove(sock)
        return self.requests

    @log
    def write_responses(self):
        """ Эхо-ответ сервера клиентам, от которых были запросы
        """

        for sock in self.w:
            if sock in self.requests:
                try:
                    # Подготовить и отправить ответ сервера
                    if self.requests[sock]['action'] == 'presence':
                        self.interlocutors[self.requests[sock]
                                           ['user']['account_name']] = sock
                        logger.info(
                            f'presence message received from client {sock.getpeername()}')
                        response = {
                            "response": 202,
                            "time": time.time(),
                            "alert": "chat-server confirm connection"
                        }
                        sock.send(pickle.dumps(response))

                except:  # Сокет недоступен, клиент отключился
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
                    except Exception as e:
                        pass

            elif self.requests[sock]['action'] == 'quit':
                print(
                    f'deleting: {self.requests[sock]["action"]}\n{self.requests[sock]}')

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
                print(f'joining : groups : {self.groups}')


if __name__ == '__main__':

    srv = Server()
