import sqlite3
import datetime
import asrmsg
import threading
import hmac
import hashlib
import time
import requests
import json
import base64

from logger import logger

class forward():
    c_dingtoken = ""
    c_dingsecret = ""
    c_loop = True

    def __init__(self, dingtoken, dingsecret) -> None:
        
        self.c_dingtoken = dingtoken
        self.c_dingsecret = dingsecret


    def dingding(self, content):
        timestamp = int(time.time() * 1000)
        sign = base64.b64encode(hmac.new(self.c_dingsecret.encode(), f"{timestamp}\n{self.c_dingsecret}".encode(), hashlib.sha256).digest()).decode('utf-8')
        url = "https://oapi.dingtalk.com/robot/send?access_token={0}&timestamp={1}&sign={2}".format(self.c_dingtoken, timestamp, sign)

        data = json.dumps({
            "msgtype": "text",
            "text": {
                "content": content
            }
        })

        headers = {
            "Content-Type": "application/json",
            "Charset": "UTF-8",
        }
        try:
            response = requests.post(url, data=data, headers=headers)
            resJson = response.json()
            if resJson['errcode'] != 0:
                logger.write("钉钉发送失败：" + content.replace("\n",""))
                logger.write("钉钉返回值：" + response.text)
        except:
            logger.write("钉钉无法发送：" + content.replace("\n",""))


    def writedb(self, device, index, smsfrom, text, smstime):
        conn = sqlite3.connect('sms.db')
        cursor = conn.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS sms (id INTEGER PRIMARY KEY AUTOINCREMENT,devive VARCHAR(100), smsindex VARCHAR(10), smsfrom VARCHAR(100), text TEXT, smstime TIMESTAMP, createtime TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')

        createtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO sms (devive, smsindex, smsfrom, text, smstime, createtime) VALUES (?, ?, ?, ?, ?, ?)", (device, index, smsfrom, text, smstime, createtime))
        conn.commit()
        conn.close()

    def threadGetSms(self, device):
        asr = asrmsg.asrmsg(device['host'],device['user'],device['passwd'])
        login = asr.login()
        if login == 1:
            logger.write(device['name'] + "初始化登录失败")
            exit()
        errorCount = 0
        while True:
            try:
                smslist = asr.setMsg()
                msg = ''
                for smsInfo in smslist:
                    self.writedb(device['name'], smsInfo['index'], smsInfo['from'], smsInfo['text'], smsInfo['time'])
                    msg += "来源：{0}\n信息：{1}\n时间：{2}\n设备：{3}\n\n".format(smsInfo['from'],smsInfo['text'],smsInfo['time'],device['name'])
                if msg != "":
                    self.dingding(msg)
                errorCount = 0
            except:
                logger.write(device['name'] + " 短信获取失败")
                errorCount += 1

            if errorCount > 5:
                msg = device['name'] + " 设备失联"
                logger.write(msg)
                self.dingding(msg)
                exit()
            
            time.sleep(1)

    def getSms(self, devices):
        for device in devices:
            thread = threading.Thread(target=self.threadGetSms,args=(device,))
            thread.daemon = True
            thread.start()
        self.loopTask()
    
    def loopTask(self):
        while self.c_loop:
            try:
                time.sleep(1)
            except KeyboardInterrupt: 
                self.c_loop = False
                exit()