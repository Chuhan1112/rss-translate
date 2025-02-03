import os
import re
import time
import hashlib
import configparser
from urllib import parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import feedparser
from pygtrans import Translate
from openai import OpenAI
from rfeed import Item, Guid, Feed

# Configuration
CONFIG_FILE = "test.ini"
README_FILE = "README.md"
BASE_DIR = "rss"
MODEL = os.getenv("MODEL")
OPENAI_API_KEY = os.getenv("API_KEY")
OPENAI_BASE_URL = s.getenv("BASE_URL")


# Prompts
SYSTEM_PROMPT = """
下面你将扮演一位有着 20 年经验的网页新闻翻译员，将下列新闻内容翻译至中文，希望你用专业、准确的中文词汇和句子替换简化的 A0 级单词和句子，
保留原文中的专有名词和术语，并提供相应的注释。保持相同的意思，但使它们更符合简洁、专业的中文新闻语言的风格,直接返回翻译结果，
不要添加任何额外信息; 对于内容中保持格式、所有HTML标签不变、保留链接和图片样式；存在多个段落时，段落之间使用p 标签,
确保返回格式符合html规范,但不要返回html代码，直接返回翻译结果，不要添加任何额外信息;
"""
TITLE_PROMPT = "下面你将扮演一位有着 20 年经验的英语政经新闻翻译员，希望你将以下新闻标题全部翻译成专业、准确的中文,直接返回翻译结果，不要添加任何额外信息"
TITLE_PICK_PROMPT = "下面你将扮演一位有着 20 年经验的英语政经新闻翻译员，根据新闻标题的英文原文和已翻译的两个备选结果，进行挑选和优化，直接返回翻译结果，不要添加任何额外信息"
class RSSTranslator:
    def __init__(self, url, source="auto", target="zh-CN"):
        self.url = url
        self.source = source
        self.target = target
        self.feed = feedparser.parse(url)
        self.google_translator = Translate()
        self.openai_translator = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    def tran_with_google(self, content):
        if not content:
            return content
        return self.google_translator.translate(content, target=self.target, source=self.source).translatedText

    def trans_with_gpt(self, prompt, content):
        if not content or self.source == "proxy":
            return content
        try:
            response = self.openai_translator.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content},
                ],
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT translation error: {e}")
            return ""

    def process_entry(self, entry):
        if not entry.title:
            return None
        print(f"Translating: {entry.title}")
        translated_title1 = self.trans_with_gpt(TITLE_PROMPT, entry.title)
        translated_description = self.trans_with_gpt(SYSTEM_PROMPT, entry.summary)
        translated_title2 = self.tran_with_google(entry.title)

        pick_content = "原文："+ entry.title+ "备选 1：" + translated_title1 + "备选 2：" + translated_title2
        title_picked = self.trans_with_gpt(TITLE_PICK_PROMPT, pick_content)
        return Item(
            title=title_picked,
            link=entry.link,
            description=translated_description,
            guid=Guid(entry.link),
            pubDate=self.get_datetime(entry),
        )

    def get_translated_feed(self, max_items=2):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.process_entry, entry): i for i, entry in enumerate(self.feed.entries[:max_items])}
            items = [future.result() for future in as_completed(futures) if future.result()]

        feed = self.feed.feed
        title = getattr(feed, 'title', None)
        if not title:
            # If there is no title, skip processing
            return None
        return Feed(
            title=self.tran_with_google(title),
            link=feed.link,
            description=self.trans_with_gpt(SYSTEM_PROMPT, self.get_subtitle(feed)),
            lastBuildDate=self.get_datetime(feed),
            items=items,
        )

    @staticmethod
    def get_datetime(entry):
        try:
            return datetime(*entry.published_parsed[:6])
        except AttributeError:
            return datetime.now()

    @staticmethod
    def get_subtitle(feed):
        return getattr(feed, 'subtitle', '')

def load_config(file_path):
    config = configparser.ConfigParser()
    with open(file_path, "r") as f:
        config.read_string(parse.unquote(f.read()))
    return config

def save_config(config, file_path):
    with open(file_path, "w") as configfile:
        config.write(configfile)

def get_config_value(config, section, key):
    return config.get(section, key).strip('"')

def set_config_value(config, section, key, value):
    config[section][key] = f'"{value}"'

def get_trans_config(config, section):
    action = get_config_value(config, section, "action")
    if action == "auto":
        return "auto", "zh-CN"
    elif action == "proxy":
        return "proxy", "proxy"
    else:
        source, target = action.split("->")
        return source, target

def translate_feed(config, section):
    name = get_config_value(config, section, "name")
    url = get_config_value(config, section, "url")
    max_items = int(get_config_value(config, section, "max"))
    source, target = get_trans_config(config, section)

    translator = RSSTranslator(url, source=source, target=target)
    translated_feed = translator.get_translated_feed(max_items=max_items)

    output_path = os.path.join(BASE_DIR, name)
    with open(output_path, "w", encoding="utf-8") as f:
        if translated_feed:
            f.write(translated_feed.rss())
        # f.write(translated_feed.rss())
    
    print(f"Translated: {url} > {output_path}")
    return f" - {section} [{url}]({url}) -> [{name}]({parse.quote(output_path)})\n"

def update_readme(links):
    with open(README_FILE, "r+", encoding="UTF-8") as f:
        content = f.readlines()
        for i, line in enumerate(content):
            if "## rss translate links" in line:
                content = content[:i+2] + links
                break
        f.seek(0)
        f.writelines(content)
        f.truncate()

def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    config = load_config(CONFIG_FILE)

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(translate_feed, config, section) for section in config.sections()[1:]]
        links = [future.result() for future in as_completed(futures)]

    update_readme(links)
    save_config(config, CONFIG_FILE)

if __name__ == "__main__":
    main()
