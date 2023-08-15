import datetime

class logger:
    @staticmethod
    def write(msg):
        msg = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S ') + msg
        print(msg)
        with open("log.log", 'a') as file:
            file.write(msg + "\n")
        
