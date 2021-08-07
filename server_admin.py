import sys
from PyQt5 import QtWidgets
from sqlalchemy.sql.expression import desc
import adm_ui

from sqlalchemy import create_engine, engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from chat_server import Client, ClientHistory

engine = create_engine('sqlite:///server_storage.sqlite')
Session = sessionmaker(bind=engine)


Storage = declarative_base()

Storage.metadata.create_all(engine)


def get_contacts():

    clients = []
    client_query = session.query(Client.login).all()
    for client in client_query:
        clients.append(client[0])
    return '\n'.join(clients)


def get_stat():

    entries = []
    entries_query = session.query(
        ClientHistory.entry_time, ClientHistory.client_id, ClientHistory.ip_addr).order_by(desc(ClientHistory.entry_time)).limit(32).all()
    for entry in entries_query:
        cl_name = session.query(Client.login).filter(
            Client.id == entry[1]).one()[0]
        entries.append(str(entry[0])[:19] + '\t' + cl_name + '\t\t' + entry[2])
    return '\n'.join(entries)


if __name__ == '__main__':

    session = Session()
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    ui = adm_ui.Ui_MainWindow()
    ui.setupUi(window)
    cl_list = get_contacts()
    ui.pushButton_1.clicked.connect(lambda: ui.listClient.setText(cl_list))
    st_list = get_stat()
    ui.pushButton_2.clicked.connect(lambda: ui.listClient_2.setText(st_list))
    window.show()
    sys.exit(app.exec_())
