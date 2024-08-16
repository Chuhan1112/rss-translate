# coding:utf-8
import configparser
from pygtrans import Translate
import os
from urllib import parse
import hashlib
import re

import concurrent.futures
from openai import OpenAI
import datetime
import time
from rfeed import Item, Guid, Feed
import feedparser
# pip install pygtrans -i https://pypi.org/simple
# ref:https://zhuanlan.zhihu.com/p/390801784
# ref:https://beautifulsoup.readthedocs.io/zh_CN/latest/
# ref:https://pygtrans.readthedocs.io/zh_CN/latest/langs.html
# client = Translate()
# text = client.translate('Google Translate')
# print(text.translatedText)  # 谷歌翻译


client = OpenAI(
    api_key=os.getenv('API_KEY'),
    base_url="https://api.siliconflow.cn/v1",
)
MODEL = os.getenv('MODEL') #"Qwen/Qwen2-7B-Instruct"


    
def remove_html_tags(text):
    # 使用正则表达式去除 HTML 标签
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def get_md5_value(src):
    _m = hashlib.md5()
    _m.update(src.encode("utf-8"))
    return _m.hexdigest()





def getTime(e):
    try:
        struct_time = e.published_parsed
    except Exception:
        struct_time = time.localtime()
    return datetime.datetime(*struct_time[:6])


def getSubtitle(e):
    try:
        sub = e.subtitle
    except:
        sub = ""
    return sub


class GoogleTran:
    def __init__(self, url, source="auto", target="zh-CN"):
        self.url = url
        self.source = source
        self.target = target

        self.d = feedparser.parse(url)
        self.GT = Translate()
    def tr(self,content):
        if not content:
            return content
        return self.GT.translate(content,target=self.target,source=self.source).translatedText
    def gpt_tr(self, content):
        if not content:
            return content
        if self.source == "proxy":  # 代理
            return content
        try:
            # print('req：{tt}'.format(tt=content))
            response = client.chat.completions.create(
                # model='alibaba/Qwen1.5-110B-Chat',
                model=MODEL,
                messages=[
                    # {'role': 'user', 'content': 'f 翻译这段文字并直接返回翻译结果,不要改动格式：： {tt}'.format(tt=tt.translatedText)}
                    {"role":"system","content":"下面你将扮演一位 20 年的网页新闻翻译员，将下列用户提供的内容翻译至中文，希望你用专业、准确的高级中文词汇和句子替换简化的 A0 级单词和句子。保持相同的意思，但使它们更符合优美、专业的中文新闻语言的风格,直接返回翻译结果，不要添加任何额外信息; 对于内容中保持格式、所有HTML标签不变、保留链接和图片样式,存在多个段落时，段落之间使用p 标签,确保返回格式符合html规范,但不要返回html代码"},
                    {
                        "role": "user",
                        "content": "{tt}".format(tt=content),
                    }
                ],
                stream=False,
            )
            # print("res:", response.choices[0].message.content)
            return response.choices[0].message.content
            # return tt.translatedText
        except:
            return ""

    def get_newconent(self, max=2):
        item_list = []
        if len(self.d.entries) < max:
            max = len(self.d.entries)
        for entry in self.d.entries[:max]:
            if not entry.title:
                continue
            one = Item(
                # title=remove_html_tags(self.tr(remove_html_tags(entry.title))),
                title= self.gpt_tr(entry.title),
                link=entry.link,
                description=self.gpt_tr(entry.summary),
                # description=entry.summary,
                guid=Guid(entry.link),
                pubDate=getTime(entry),
            )
            item_list += [one]
        feed = self.d.feed
        if not feed.title:
            return ""
        newfeed = Feed(
            # title=remove_html_tags(self.tr(remove_html_tags(feed.title))),
            title=self.gpt_tr(feed.title),
            link=feed.link,
            description=self.gpt_tr(getSubtitle(feed)),
            lastBuildDate=getTime(feed),
            items=item_list,
        )
        return newfeed.rss()


with open("test.ini", mode="r") as f:
    ini_data = parse.unquote(f.read())
config = configparser.ConfigParser()
config.read_string(ini_data)
secs = config.sections()


def get_cfg(sec, name):
    return config.get(sec, name).strip('"')


def set_cfg(sec, name, value):
    config[sec][name] = '"%s"' % value


def get_cfg_tra(sec):
    cc = config.get(sec, "action").strip('"')
    target = ""
    source = ""
    if cc == "auto":
        source = "auto"
        target = "zh-CN"

    elif cc == "proxy":
        source = "proxy"
        target = "proxy"
    else:
        source = cc.split("->")[0]
        target = cc.split("->")[1]
    return source, target


BASE = get_cfg("cfg", "base")
try:
    os.makedirs(BASE)
except:
    pass
links = []


def tran(sec):
    out_dir = BASE + get_cfg(sec, "name")
    url = get_cfg(sec, "url")
    max_item = int(get_cfg(sec, "max"))
    old_md5 = get_cfg(sec, "md5")
    source, target = get_cfg_tra(sec)
    global links

    links += [
        " - %s [%s](%s) -> [%s](%s)\n"
        % (sec, url, (url), get_cfg(sec, "name"), parse.quote(out_dir))
    ]

    # new_md5= get_md5_value(url) # no use now

    # if old_md5 == new_md5:
    #     return
    # else:
    #     set_cfg(sec,'md5',new_md5)

    c = GoogleTran(url, target=target, source=source).get_newconent(max=max_item)

    with open(out_dir, "w", encoding="utf-8") as f:
        f.write(c)
        # print(c)
        # f.write(content)
    print("GT: " + url + " > " + out_dir)


# for x in secs[1:]:
#     tran(x)
#     print(config.items(x))
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(tran, x) for x in secs[1:]]
    for future in concurrent.futures.as_completed(futures):
        try:
            future.result()
        except Exception as e:
            print(f"Error processing section: {e}")


with open("test.ini", "w") as configfile:
    config.write(configfile)


def get_idx(l):
    for idx, line in enumerate(l):
        if "## rss translate links" in line:
            return idx + 2


YML = "README.md"

f = open(YML, "r+", encoding="UTF-8")
list1 = f.readlines()
list1 = list1[: get_idx(list1)] + links

f = open(YML, "w+", encoding="UTF-8")
f.writelines(list1)
f.close()
