import hashlib
import requests
import re
import random
import time
import xml.etree.ElementTree as ET

class asrmsg:
    c_host = ''
    c_user = ''
    c_pass = ''

    # 首次登录服务器返回登录固定值
    c_realm = ''
    c_nonce = ''
    c_qop = ''

    c_count = 0

    def __init__(self, host,user,passwd) :
        self.c_host = host
        self.c_user = user
        self.c_pass = passwd

    def getValue(self, text):
        return re.search('="(.*?)"',text).group(1)
    
    def md5(self, text):
        md5_hash = hashlib.md5()
        md5_hash.update(text.encode('utf-8'))
        return md5_hash.hexdigest()
    
    def getAuthHeader(self, reqType):
        HA1 = self.md5(self.c_user + ":" + self.c_realm + ":" + self.c_pass)
        HA2 = self.md5(reqType + ":/cgi/xml_action.cgi")

        rand = random.randint(0,100000)
        datestamp = int(time.time() * 1000)

        salt = str(rand) + str(datestamp)
        cnonce =  self.md5(salt)[:16]

        authcount = ( "0000000000" + str(hex(self.c_count)) )[-8:]
        DigestRes = self.md5(":".join([HA1,self.c_nonce,authcount,cnonce,self.c_qop,HA2]))
        self.c_count += 1
        authHeader = 'Digest username="{0}", realm="{1}", nonce="{2}", uri="{3}", response="{4}", qop={5}, nc={6}, cnonce="{7}"'.format(self.c_user, self.c_realm, self.c_nonce, "/cgi/xml_action.cgi", DigestRes, self.c_qop, authcount, cnonce)

        return authHeader



    def login(self):
        try:
            url = "http://" + self.c_host + "/login.cgi"
            response = requests.get(url, timeout=5)
            loginParam = response.headers.get("WWW-Authenticate")
            loginParamArray = loginParam.split(" ")
            if loginParamArray[0] == "Digest":
                self.c_realm = self.getValue(loginParamArray[1])
                self.c_nonce = self.getValue(loginParamArray[2])
                self.c_qop = self.getValue(loginParamArray[3])

                HA1 = self.md5(self.c_user + ":" + self.c_realm + ":" + self.c_pass)
                HA2 = self.md5("GET:/cgi/protected.cgi")

                rand = random.randint(0,100000)
                datestamp = int(time.time() * 1000)

                salt = str(rand) + str(datestamp)
                cnonce =  self.md5(salt)[:16]
                DigestRes = self.md5(HA1 + ":" + self.c_nonce + ":00000001:" + cnonce + ":" + self.c_qop + ":" + HA2)

                urlparam = {
                    "Action": "Digest",
                    "username": self.c_user,
                    "realm": self.c_realm,
                    "nonce": self.c_nonce,
                    "response": DigestRes,
                    "qop": self.c_qop,
                    "cnonce": cnonce,
                    "temp": "asr"
                }
                headers = {
                    "Authorization": self.getAuthHeader("GET"),
                    "Expires": "-1",
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Pragma": "no-cache"
                }
                response = requests.get(url,params=urlparam,headers=headers, timeout=5)
                if "200 OK" in response.text:
                    return 0
                elif "500 OK" in response.text:
                    return 1
            return 2
        except requests.exceptions.RequestException:
            return 2

    def setMsg(self):
        xml = ''
        for i in range(3):
            url = "http://" + self.c_host + "/xml_action.cgi?method=set&module=duster&file=message"
            headers = {
                "Authorization": self.getAuthHeader("POST"),
                "Content-Type": "application/xml"
            }
            xmldata = '<?xml version="1.0" encoding="US-ASCII"?> <RGW><message><flag><message_flag>GET_RCV_SMS_LOCAL</message_flag></flag><get_message><page_number>1</page_number></get_message></message></RGW>'
            response = requests.post(url, data=xmldata, headers=headers, timeout=5)
            if response.text.strip() == "":
                self.login()
            else:
                xml = response.text
                break
        if xml == '':
            return False
        else:
            msglist = self.formatXml(xml)
            idlist = [item['index'] for item in msglist]
            self.deleteMsg(idlist)
            return msglist


    def deleteMsg(self,idlist):
        url = "http://" + self.c_host + "/xml_action.cgi?method=set&module=duster&file=message"
        headers = {
            "Authorization": self.getAuthHeader("POST"),
            "Content-Type": "application/xml"
        }
        xmldata = '<?xml version="1.0" encoding="US-ASCII"?> <RGW><message><flag><message_flag>DELETE_SMS</message_flag><sms_cmd>6</sms_cmd></flag><get_message><tags>12</tags><mem_store>1</mem_store></get_message><set_message><delete_message_id>'+','.join(idlist)+',</delete_message_id></set_message></message></RGW>'
        response = requests.post(url, data=xmldata, headers=headers, timeout=5)
        return response.text
        

    def getmsg(self):
        xml = ''
        for i in range(3):
            url = "http://" + self.c_host + "/xml_action.cgi?method=get&module=duster&file=message"
            headers = {
                "Authorization": self.getAuthHeader("GET")
            }
            response = requests.get(url,headers=headers, timeout=5)

            if response.text.strip() == "":
                self.login()
            else:
                xml = response.text
                break
        if xml == "":
            raise Exception("登录失败")
        return xml
    
    def formatXml(self, xml):
        if xml == "":
            return []

        xmldata = ET.fromstring(xml)
        items = xmldata.findall(".//Item")

        msglist = []
        for item in items:
            # if item.find('status').text == "1":
            #     continue

            msgOriTime = item.find('received').text
            msgOTArray = msgOriTime.split(",")
            msgTime = "{0}-{1}-{2} {3}:{4}:{5}".format(msgOTArray[0],msgOTArray[1],msgOTArray[2],msgOTArray[3],msgOTArray[4],msgOTArray[5])

            msgIndex = item.find('index').text
            msgFrom = bytes.fromhex(item.find('from').text).decode('utf-16be')
            msgText = bytes.fromhex(item.find('subject').text).decode('utf-16be')

            msgInfo = {
                "index": msgIndex,
                "from": msgFrom,
                "text": msgText,
                "time": msgTime
            }
            msglist.append(msgInfo)

        return msglist