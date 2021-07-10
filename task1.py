"""Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов. 
Аргументом функции является список, в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом. 
В функции необходимо перебирать ip-адреса и проверять их доступность с выводом соответствующего сообщения («Узел доступен», «Узел недоступен»). 
При этом ip-адрес сетевого узла должен создаваться с помощью функции ip_address().
"""
import os
import ipaddress
import subprocess
HOST_LIST = ['192.168.1.39', 'google.ru', '192.168.1.99', ]


def host_ping(host_list):
    for host in host_list:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = host
        arg = "ping -w3 " + str(address)
        pp = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        out = pp.stdout.read()
        if "100% packet loss" in out.decode():
            print(f'Узел {address} недоступен')
        else:
            print(f'Узел {address} доступен')


host_ping(HOST_LIST)
