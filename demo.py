import pyttsx3
import websocket
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import pyaudio
import sys

import requests



STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识

question = ['你是谁', '我是张智文，我是傻逼',
            '介绍一下你自己', '我是张智文，张继昌是我亲爹',
            '来个顺口溜', '智文是你儿，你是智文爹',
            '顺口溜', '你是我爹总行了吧',
            '猜猜我是谁', '你是张智文的亲爹',
            '我是你爹', '爸爸早上好',
            '叫爸爸','我爸是张继昌',
            '我是张继昌他爹','他明明是你爹',
            '你叫什么','我叫张智文，外号叫智障',
            '张继昌是我儿子','我操你妈的，傻逼玩意，鸡巴不大，事倒不少。',
            '','能不能说个话，说话像放屁一样偷偷摸摸的']
class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret


        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo":1,"vad_eos":10000}

    # 生成url
    def create_url(self):
        url = 'wss://ws-api.xfyun.cn/v2/iat'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url


# 收到websocket消息的处理

def on_message(ws, message):


    result = ''
    try:
        code = json.loads(message)["code"]
        sid = json.loads(message)["sid"]
        if code != 0:
            errMsg = json.loads(message)["message"]
            print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))

        else:
            data = json.loads(message)["data"]["result"]["ws"]

            for i in data:
                for w in i["cw"]:
                    result += w["w"]

                if result == '。' or result=='？' or result=='，':
                    result = ''
                    pass
            if result == "再见" or result == "退出":
                print("用户："+result)
                sys.exit()

            elif result in question:
                print ( "用户: %s" % (result) )
                # reply是机器人回答的话
                reply = question[question.index ( result ) + 1]

            else:
                print("用户: %s" % (result))
                # 根据语音识别文字给出智能回答
                #此处是青云客的智能机器人api
                url = "http://api.qingyunke.com/api.php?key=free&appid=0&msg=" + result
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 \
                                                   (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
                       'Host': 'api.qingyunke.com'
                       }
                response = requests.get ( url, headers=headers )
                reply = json.loads ( response.text )['content'].replace ( '{br}', '/n' )

    except Exception as e:
        print("receive msg,but parse exception:", e)
    #输出回答
    print ( "张智文:" + reply )


    # 语音合成
    # 初始化语音
    engine = pyttsx3.init ()
    # 设置语速
    rate = engine.getProperty ( 'rate' )
    engine.setProperty ( 'rate', rate - 50 )
    # 输出语音

    engine.say ( reply )  # 合成语音
    engine.runAndWait ()

# 收到websocket错误的处理
def on_error(ws, error):
    print("### error:", error)


# 收到websocket关闭的处理
def on_close(ws):
    pass
    # print("### closed ###")


# 收到websocket连接建立的处理
def on_open(ws):
    def run(*args):
        status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧
        CHUNK = 520                 # 定义数据流块
        FORMAT = pyaudio.paInt16  # 16bit编码格式
        CHANNELS = 1  # 单声道
        RATE = 16000  # 16000采样频率
        p = pyaudio.PyAudio()
        # 创建音频流
        stream = p.open(format=FORMAT,  # 音频流wav格式
                        channels=CHANNELS,  # 单声道
                        rate=RATE,  # 采样率16000
                        input=True,
                        frames_per_buffer=CHUNK)

        print("- - - - - - - Start Recording ...- - - - - - - ")

        for i in range(0,int(RATE/CHUNK*60)):
            buf = stream.read(CHUNK)
            if not buf:
                status = STATUS_LAST_FRAME
            if status == STATUS_FIRST_FRAME:

                d = {"common": wsParam.CommonArgs,
                     "business": wsParam.BusinessArgs,
                     "data": {"status": 0, "format": "audio/L16;rate=16000",
                              "audio": str(base64.b64encode(buf), 'utf-8'),
                              "encoding": "raw"}}
                d = json.dumps(d)
                ws.send(d)
                status = STATUS_CONTINUE_FRAME
                # 中间帧处理
            elif status == STATUS_CONTINUE_FRAME:
                d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                              "audio": str(base64.b64encode(buf), 'utf-8'),
                              "encoding": "raw"}}
                ws.send(json.dumps(d))

            # 最后一帧处理
            elif status == STATUS_LAST_FRAME:
                d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                              "audio": str(base64.b64encode(buf), 'utf-8'),
                              "encoding": "raw"}}
                ws.send(json.dumps(d))
                time.sleep(1)
                break

        stream.stop_stream()
        stream.close()
        p.terminate()
        ws.close()
    thread.start_new_thread(run,())


# def run():
if __name__ == "__main__":
    # global wsParam
    #此处是讯飞语音的api接口
    wsParam = Ws_Param(APPID='03bxxxxx', APIKey='714f58a9fc5fccd12fa6cd94492xxxxx',
                       APISecret='NGM5NTE2YTlmODExZDg1MGYyZjxxxxx')
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_timeout=5)
