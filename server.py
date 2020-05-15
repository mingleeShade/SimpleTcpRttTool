import threading
import time
import socket
import json
import logging

# coding:utf-8

class RecvThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global is_termial
        logger.info("recv thread start to run")
        while is_termial == False:
            recv_to_buf()
            time.sleep(0.002)
        logger.info("RecvThread end!")

class SendThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global is_termial
        logger.info("send thread start to run")
        while is_termial == False:
            send_to_net()
            time.sleep(0.002)
        logger.info("SendThread end!")


class LogicThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        logger.info("logic thread start to run")
        global is_termial
        while is_termial == False:
            #logger.info("enter logic frame.")
            process_msgs()
            #time.sleep(0.01)
        logger.info("LogicThread end!")

def process_msgs():
    reqList = recv_from_buf()
    if reqList == None:
        return
    for strReq in reqList:
        if len(strReq) == 0:
            break
        req = json.loads(strReq)
        #logger.info("recv msg, sn: %d, cmd: %s"%(req["sn"], req["cmd"]))
        if req["cmd"] == "terminal":
            is_termial = True
            logger.info("server will be terminal!")
            return
        ack = req
        ack["cmd"] = "ack"
        strAck = json.dumps(ack)
        send_to_buf(strAck)

def recv_to_buf():
    global recv_buf
    global recv_lock
    global is_termial
    recv_data = new_client_socket.recv(1024)
    if len(recv_data) == 0:
        logger.warn("recv empty!")
        is_termial = True
        return

    #logger.info("recv data len: %d"%len(recv_data))
    recv_lock.acquire()
    recv_buf = recv_buf + recv_data
    recv_lock.release()

def send_to_net():
    global send_buf
    global send_lock
    if len(send_buf) == 0:
        return
    send_lock.acquire()
    send_data = send_buf
    send_buf = ""
    send_lock.release()

    new_client_socket.send(send_data)
    logger.info("send %d"%len(send_data))

def recv_from_buf():
    global recv_buf
    global recv_lock
    recv_lock.acquire()
    if len(recv_buf) == 0:
        recv_lock.release()
        return None
    #recv_buf
    reqList = recv_buf.split(';')
    if recv_buf[-1] == ';':
        recv_buf = ""
    else:
        recv_buf = reqList[-1]
        reqList.pop()
    recv_lock.release()
    return reqList

def send_to_buf(str):
    global send_buf
    global send_lock
    send_lock.acquire()
    send_buf = send_buf + str + ";"
    send_lock.release()

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '[%(levelname)s %(asctime)s] %(message)s [Func]%(funcName)s [Line]%(lineno)d')
    logger = logging.getLogger(__name__)

    logger.info("server start!")

    is_termial = False
    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_socket.bind(("", 7890))
    tcp_server_socket.listen(128)

    new_client_socket, client_addr = tcp_server_socket.accept()
    logger.info("client connected: %s" %(client_addr, ))

    recv_lock = threading.Lock()
    recv_buf = ""
    send_lock = threading.Lock()
    send_buf = ""

    recv_thread = RecvThread()
    recv_thread.start()

    send_thread = SendThread()
    send_thread.start()

    logic_thread = LogicThread()
    logic_thread.start()

    recv_thread.join()
    send_thread.join()
    logic_thread.join()

    logger.info("server terminal!")

