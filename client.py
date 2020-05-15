import threading
import time
import socket
import json
import logging

# coding:utf-8

def get_milli_time():
    return int(round(time.time() * 1000))

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
        global interval
        while is_termial == False:
            #logger.info("enter logic frame.")
            process_msgs()
            make_reqs()
            time.sleep(interval)
        logger.info("LogicThread end!")

def process_msgs():
    ackList = recv_from_buf()
    if ackList == None:
        return

    global total_cost_time
    global near_cost_time
    global total_ack_count
    global near_ack_count
    global total_max_cost
    global near_max_cost
    for strAck in ackList:
        if len(strAck) == 0:
            break
        ack = json.loads(strAck)
        #logger.info("recv msg, sn: %d, cmd: %s"%(ack["sn"], ack["cmd"]))
        req_time = ack["req_time"]
        now = get_milli_time()
        rtt = now - req_time

        total_cost_time = total_cost_time + rtt
        total_ack_count = total_ack_count + 1
        if rtt > total_max_cost:
            total_max_cost = rtt

        if near_ack_count >= 100:
            near_avg_rtt = near_cost_time / near_ack_count
            total_avg_rtt = total_cost_time / total_ack_count
            logger.info("near 100: {avg rtt: %d, max rtt: %d}"%(near_cost_time / near_ack_count, near_max_cost) +
                    "total: {avg rtt: %d, max rtt: %d}"%(total_avg_rtt, total_max_cost))
            near_cost_time = 0
            near_ack_count = 0
            near_max_cost = 0

        near_cost_time = near_cost_time + rtt
        near_ack_count = near_ack_count + 1
        if rtt > near_max_cost:
            near_max_cost = rtt

def make_reqs():
    for i in range(send_count):
        make_req()
    #logger.info("send finish!")

def make_req():
    global sn
    req = {"sn": sn, "cmd": "req", "req_time": get_milli_time()}
    #logger.info("make req, sn: %d"%sn)
    sn = sn + 1
    strReq = json.dumps(req)
    send_to_buf(strReq)

def recv_to_buf():
    global recv_buf
    global recv_lock
    global is_termial
    recv_data = tcp_client_socket.recv(1024)
    if len(recv_data) == 0:
        logger.warn("recv empty!")
        is_termial = True
        return

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

    tcp_client_socket.send(send_data)
    #logger.info("send len after: %d" %len(send_data))

def recv_from_buf():
    global recv_buf
    global recv_lock
    recv_lock.acquire()
    if len(recv_buf) == 0:
        recv_lock.release()
        return None
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
    #logger.info("send to buf len: %d" %len(str))

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '[%(levelname)s %(asctime)s] %(message)s [Func]%(funcName)s [Line]%(lineno)d')
    logger = logging.getLogger(__name__)

    is_termial = False
    tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    logger.info("client start!")

    addr = ("10.94.28.69", 7890)
    tcp_client_socket.connect(addr)
    logger.info("connect to server: %s" %(addr,))

    recv_lock = threading.Lock()
    recv_buf = ""
    send_lock = threading.Lock()
    send_buf = ""

    #global value
    total_cost_time = 0
    near_cost_time = 0
    total_ack_count = 0
    near_ack_count = 0
    total_max_cost = 0
    near_max_cost = 0

    sn = 1
    send_count = 100
    interval = 0.01

    recv_thread = RecvThread()
    recv_thread.start()

    send_thread = SendThread()
    send_thread.start()

    logic_thread = LogicThread()
    logic_thread.start()

    recv_thread.join()
    send_thread.join()
    logic_thread.join()

    tcp_client_socket.close()
    logger.info("client terminal!")
