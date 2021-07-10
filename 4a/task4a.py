"""Реализовать скрипт, запускающий два клиентских приложения: на чтение чата и на запись в него.
"""
import subprocess
import threading

def start_client(mode):
	p = subprocess.Popen("python3 chat_client.py localhost", shell=True, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	s = mode.encode()
	out, err = p.communicate(s)

t1 = threading.Thread(target=start_client, args=('r', ))
t1.start()

t2 = threading.Thread(target=start_client, args=('s', ))
t2.start()
"""В реализации модуля клиента с прошлого курса (с предпоследнего, 7 урока) выбор режима чтения/записи мною реализован 
после запуска клиента предложением ввести буквы 'r' или 's' соответственно
"""