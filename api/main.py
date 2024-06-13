from fastapi import FastAPI
import uvicorn
import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from database.db_api import *
from config import CONFIG

app = FastAPI(docs_url=None, redoc_url=None)
OUTDATE_CLEAN = CONFIG['OUTDATE_CLEAN']


@app.get("/all", tags=["PUBLIC_API"], summary="返回完整统计信息")
def all(start: int = 0, end: int = -1, rule: str = "updated"):
    """返回数据库统计信息和文章信息列表
    - start: 文章信息列表从 按rule排序后的顺序 的开始位置
    - end: 文章信息列表从 按rule排序后的顺序 的结束位置
    - rule: 文章排序规则（创建时间created/更新时间updated）
    """
    list_ = ['title', 'created', 'updated', 'link', 'author', 'avatar']
    return query_all(list_, start, end, rule)


@app.get("/friend", tags=["PUBLIC_API"], summary="返回所有友链")
def friend():
    """返回数据库友链列表
    """
    return query_friend()


@app.get("/randomfriend", tags=["PUBLIC_API"], summary="返回随机友链")
def random_friend(num: int = 1):
    """
    随机返回num个友链信息：
    - num=1，返回友链信息的字典
    - num>1，返回包含num个友链信息字典的列表
    """
    return query_random_friend(num)


@app.get("/randompost", tags=["PUBLIC_API"], summary="返回随机文章")
def random_post(num: int = 1):
    """
    随机返回num篇文章信息：
    - num=1，返回文章信息的字典
    - num>1，返回包含num个文章信息字典的列表
    """
    return query_random_post(num)


@app.get("/post", tags=["PUBLIC_API"], summary="返回指定链接的所有文章")
def post(user: str = None, num: int = -1, rule: str = "created"):
    """返回指定链接的数据库内文章信息列表
    - user: 作者名
    - num: 指定链接的文章信息列表 按rule排序后的顺序的前num篇
    - rule: 文章排序规则（创建时间/更新时间）
    """
    return query_post(user, num, rule)


@app.get("/friendstatus", tags=["PUBLIC_API"], summary="按照指定时间划分失联/未失联的友链信息")
def friend_status(days: int = OUTDATE_CLEAN):
    """按照指定时间划分失联/未失联的友链信息，默认距离今天2个月以上（60天以上）判定为失联友链
    days: 默认为60天，取自配置文件settings.py中的OUTDATE_CLEAN
    """
    return query_friend_status(days)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True)