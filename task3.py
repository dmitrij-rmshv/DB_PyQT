"""Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2. 
Но в данном случае результат должен быть итоговым по всем ip-адресам, 
представленным в табличном формате (использовать модуль tabulate)
"""
import ipaddress
import subprocess
from itertools import zip_longest
from tabulate import tabulate


def host_range_ping_tab(ip_1, ip_2):
    reachable = ["Reachable", ]
    unreachable = ["Unreachable", ]
    try:
        address_start = ipaddress.ip_address(ip_1)
        address_end = ipaddress.ip_address(ip_2)
    except ValueError:
        pass
    current_address = address_start
    while current_address <= address_end:
        if str(current_address).split('.')[:3] == str(address_start).split('.')[:3]:

            try:
                address = ipaddress.ip_address(current_address)
            except ValueError:
                pass
            arg = "ping -w2 " + str(current_address)
            pp = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
            out = pp.stdout.read()
            if "100% packet loss" in out.decode():
                unreachable.append(str(current_address))
            else:
                reachable.append(str(current_address))
        current_address += 1
    transp = list(zip_longest(reachable, unreachable))
    print(tabulate(transp, headers='firstrow', tablefmt="pipe"))


host_range_ping_tab('192.168.1.33', '192.168.1.44')
