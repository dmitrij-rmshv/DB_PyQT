"""Реализовать скрипт, запускающий указанное количество клиентских приложений.
"""
import subprocess
import threading

def start_client():
	p = subprocess.Popen("python3 chat_client.py localhost", shell=True, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)

number_of_clients = int(input("Введите необходимое количество запускаемых клиентов: "))
for i in range(number_of_clients):
	start_client()

