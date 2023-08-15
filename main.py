from forward import forward

devices = [
    {
        "name": "SMS1",
        "host": "192.168.1.1",
        "user": "admin",
        "passwd": "",
    },
    {
        "name": "SMS2",
        "host": "192.168.0.1",
        "user": "admin",
        "passwd": "",
    }
]
dingtoken = ""
dingsecret = ""

def main():
    print("ASR短信转发 https://github.com/fxnetw/asr-sms-forward")
    fw = forward(dingtoken,dingsecret)
    fw.getSms(devices)

if __name__ == "__main__":
    main()