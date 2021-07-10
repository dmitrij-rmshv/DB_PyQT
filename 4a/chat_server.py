from socket import socket, AF_INET, SOCK_STREAM
import time
import pickle
from sys import argv
from argparse import ArgumentParser
import logging
import log.server_log_config
import select


logger = logging.getLogger('server_app')

def log(func):
    def deco(*args, **kwargs):
        logger.info(f'function "{func.__name__}"" running')
        r = func(*args, **kwargs)        
        return r
    return deco

@log
def new_listen_socket(sock_parms):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind((sock_parms.address, int(sock_parms.port)))
    sock.listen(5)
    sock.settimeout(0.2)
    return sock

@log
def create_parser():
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=7777)
    parser.add_argument('-a', '--address', default='')
    return parser

def read_requests(r_clients, all_clients):
    """ Чтение запросов из списка клиентов
    """
    requests = {}  # Словарь запросов клиентов вида {сокет: запрос}

    for sock in r_clients:
        try:
            requests[sock] = pickle.loads(sock.recv(640))
        except:
            # print('Клиент {} {} отключился'.format(sock.fileno(), sock.getpeername()))
            print('Клиент  отключился')
            all_clients.remove(sock)
    return requests

@log
def write_responses(requests, w_clients, all_clients):
    """ Эхо-ответ сервера клиентам, от которых были запросы
    """

    for sock in w_clients:
        if sock in requests:
            try:
                # Подготовить и отправить ответ сервера
                if requests[sock]['action'] == 'presence':
                    logger.info(f'presence message received from client {sock.getpeername()}')
                    response = {
                        "response": 202,
                        "time": time.time(),
                        "alert": "chat-server confirm connection"
                    }
                    sock.send(pickle.dumps(response))

            except:  # Сокет недоступен, клиент отключился
                print('Клиент {} {} отключился'.format(sock.fileno(), sock.getpeername()))
                sock.close()
                all_clients.remove(sock)

    for sock in requests:
        if requests[sock]['action'] == 'msg':
            response = requests[sock]
            msg_copy = requests[sock]['message']
            logger.info(f'text message "{msg_copy}" received from client {sock.getpeername()}')
            for receiver in all_clients:
                receiver.send(pickle.dumps(response))


def main():
    arg = create_parser().parse_args(argv[1:])
    s = new_listen_socket(arg)
    clients = []


    while True:
        try:
            conn, addr = s.accept()  # Проверка подключений
        except OSError as e:
            pass                        # timeout вышел
        else:
            print(f'Получен запрос на соединение с {str(addr)}')
            clients.append(conn)
        finally:
            # Проверить наличие событий ввода-вывода без таймаута
            wait = 3
            r = []
            w = []
            try:
                r, w, e = select.select(clients, clients, [], wait)
            except Exception as e:
            # Исключение произойдет, если какой-то клиент отключится
                pass        # Ничего не делать, если какой-то клиент отключился
            
            requests = read_requests(r, clients)  # Сохраним запросы клиентов
            if requests:
                write_responses(requests, w, clients)  # Выполним отправку ответов клиентам



if __name__ == '__main__':

    main()
