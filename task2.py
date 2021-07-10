"""Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона. 
Меняться должен только последний октет каждого адреса. 
По результатам проверки должно выводиться соответствующее сообщение.
"""
import ipaddress


def host_range_ping(ip_1, ip_2):
    try:
        address_start = ipaddress.ip_address(ip_1)
        address_end = ipaddress.ip_address(ip_2)
    except ValueError:
        pass
    current_address = address_start
    # print(net)
    while current_address <= address_end:
        if str(current_address).split('.')[:3] == str(address_start).split('.')[:3]:
            print(current_address)
        current_address += 1


host_range_ping('192.168.1.33', '192.168.1.44')
