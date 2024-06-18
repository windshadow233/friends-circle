from urllib import parse
from datetime import datetime, timedelta

from .utils import *

def query_all(li, start: int = 0, end: int = -1, rule: str = "updated"):
    conn = db_manager.db_init()
    cursor = conn.cursor()

    # 获取文章总数
    cursor.execute('SELECT COUNT(*) FROM posts')
    article_num = cursor.fetchone()[0]

    # 检查start、end的合法性
    start, end, message = start_end_check(start, end, article_num)
    if message:
        return {"message": message}

    # 检查rule的合法性
    if rule != "created" and rule != "updated":
        return {"message": "rule error, please use 'created'/'updated'"}

    # 查询文章数据
    query = f"SELECT * FROM posts ORDER BY {rule} DESC LIMIT {end - start} OFFSET {start}"
    cursor.execute(query)
    posts = cursor.fetchall()

    # 查询最后更新时间
    cursor.execute("SELECT createAt FROM posts ORDER BY updated DESC LIMIT 1000")
    last_update_time = cursor.fetchone()[0]

    # 统计好友数量、活跃好友数量、错误数量
    cursor.execute("SELECT COUNT(*) FROM friends")
    friends_num = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM friends WHERE error=0")
    active_num = cursor.fetchone()[0]
    error_num = friends_num - active_num

    # 构造返回数据
    data = {}
    data['statistical_data'] = {
        'friends_num': friends_num,
        'active_num': active_num,
        'error_num': error_num,
        'article_num': article_num,
        'last_updated_time': last_update_time
    }

    post_data = []
    for k, post in enumerate(posts):
        item = {'floor': start + k + 1}
        for elem in li:
            item[elem] = post[elem]
        post_data.append(item)

    conn.close()
    data['article_data'] = post_data
    return data

def query_friend():
    conn = db_manager.db_init()
    cursor = conn.cursor()

    # 查询前1000个好友
    cursor.execute('SELECT * FROM friends LIMIT 1000')
    friends = cursor.fetchall()

    conn.close()

    friend_list_json = []
    if friends:
        for friend in friends:
            item = {
                'name': friend['name'],
                'link': friend['link'],
                'avatar': friend['avatar']
            }
            friend_list_json.append(item)
    else:
        return {"message": "not found"}

    return friend_list_json


def query_random_friend(num):
    if num < 1:
        return {"message": "param 'num' error"}

    conn = db_manager.db_init()
    cursor = conn.cursor()

    # 查询 num 个随机好友
    cursor.execute(f'SELECT * FROM friends ORDER BY RANDOM() LIMIT {num}')
    data = cursor.fetchall()

    conn.close()

    friend_list_json = []
    if data:
        for d in data:
            itemlist = {
                'name': d['name'],
                'link': d['link'],
                'avatar': d['avatar']
            }
            friend_list_json.append(itemlist)
    else:
        # data为空直接返回
        return {"message": "not found"}

    return friend_list_json[0] if len(friend_list_json) == 1 else friend_list_json


def query_random_post(num):
    if num < 1:
        return {"message": "param 'num' error"}

    conn = db_manager.db_init()
    cursor = conn.cursor()

    # 查询 num 个随机文章
    cursor.execute(f'SELECT * FROM posts ORDER BY RANDOM() LIMIT {num}')
    data = cursor.fetchall()

    conn.close()

    post_list_json = []
    if data:
        for d in data:
            itemlist = {
                "title": d['title'],
                "created": d['created'],
                "updated": d['updated'],
                "link": d['link'],
                "author": d['author'],
                "avatar": d['avatar'],
            }
            post_list_json.append(itemlist)
    else:
        # data为空直接返回
        return {"message": "not found"}

    return post_list_json[0] if len(post_list_json) == 1 else post_list_json


def query_post(user, num):
    conn = db_manager.db_init()
    cursor = conn.cursor()
    if user is None:
        # 查询没有错误的用户，随机排序并选择第一个
        cursor.execute("SELECT * FROM friends WHERE error=0 ORDER BY RANDOM() LIMIT 1")
        user = cursor.fetchone()
    else:
        cursor.execute('SELECT * FROM friends WHERE name = ?', (user,))
        user = cursor.fetchone()

    # 如果链接不匹配，则返回错误信息
    if user is None:
        return {"message": "not found"}

    # 查询用户的文章
    cursor.execute('SELECT * FROM posts WHERE author = ? ORDER BY RANDOM() LIMIT ?', (user['name'], num))
    posts = cursor.fetchall()

    conn.close()

    data = []
    for floor, post in enumerate(posts):
        itemlist = {
            "title": post['title'],
            "link": post['link'],
            "created": post['created'],
            "updated": post['updated'],
            "floor": floor + 1
        }
        data.append(itemlist)

    api_json = {
        "statistical_data": {
            "name": user['name'],
            "link": user['link'],
            "avatar": user['avatar'],
            "article_num": len(posts)
        },
        "article_data": data
    }

    return api_json


def query_friend_status(days):
    # 初始化数据库连接
    conn = db_manager.db_init()
    cursor = conn.cursor()

    # 查询所有文章
    cursor.execute('SELECT * FROM posts')
    posts = cursor.fetchall()

    # 查询所有好友
    cursor.execute('SELECT * FROM friends')
    friends = cursor.fetchall()

    # 构建好友名字到链接的映射
    name_2_link_map = {friend['name']: friend['link'] for friend in friends}

    # 初始化友链状态信息
    friend_status = {
        "total_friend_num": len(name_2_link_map),
        "total_lost_num": 0,
        "total_not_lost_num": 0,
        "lost_friends": {},
        "not_lost_friends": {},
    }

    # 检查每篇文章的更新时间，更新友链状态信息
    not_lost_friends = {}
    for post in posts:
        updated_time = datetime.strptime(post['createAt'], r'%Y-%m-%d %H:%M:%S')
        if datetime.now() - updated_time <= timedelta(days=days):
            # 未超过指定天数，未失联
            author = post['author']
            if author in name_2_link_map:
                not_lost_friends[author] = name_2_link_map.pop(author)

    # 更新统计信息和失联友链信息
    friend_status["total_not_lost_num"] = len(not_lost_friends)
    friend_status["total_lost_num"] = friend_status["total_friend_num"] - friend_status["total_not_lost_num"]
    friend_status["not_lost_friends"] = not_lost_friends
    friend_status["lost_friends"] = name_2_link_map

    conn.close()
    return friend_status
