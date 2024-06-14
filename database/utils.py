import sqlite3
import os
from datetime import datetime
from config import *

db = CONFIG['db']

def start_end_check(start, end, article_num):
    """
    检查start、end的合法性：
    1、article_num必须小于等于1000：article_num<=1000
    2、end如果为-1，则取文章数作为end
    3、start必须大于等于0且小于end：0<=start<end
    4、end必须小于等于文章数：end<=article_num
    :return:
    """
    message = ""
    article_num = min(article_num, 1000)

    if end == -1:
        end = article_num
    elif end > article_num:
        end = article_num

    if start < 0 or start >= end:
        message = "start error"

    return start, end, message

class DBManager():

    def create_db(self):
        if os.path.isfile(db):
            return
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(256),
            link VARCHAR(1024) UNIQUE,
            avatar VARCHAR(1024),
            error BOOLEAN,
            createAt DATETIME DEFAULT (datetime(CURRENT_TIMESTAMP, '+8 hours'))
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(256),
            created VARCHAR(256),
            updated VARCHAR(256),
            link VARCHAR(1024) UNIQUE,
            author VARCHAR(256),
            avatar VARCHAR(1024),
            createAt DATETIME DEFAULT (datetime(CURRENT_TIMESTAMP, '+8 hours'))
        )
        ''')

        conn.commit()
        conn.close()

    def db_init(self):
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        return conn
    
    def insert_friends(self, friends):
        insert = 0
        update = 0
        conn = self.db_init()
        cursor = conn.cursor()
        for friend in friends:
            cursor.execute('''
            UPDATE friends
            SET name = ?, avatar = ?, error = ?
            WHERE link = ?;
            ''', (friend['name'], friend['avatar'], friend['error'], friend['link']))
            if cursor.rowcount == 0:
                cursor.execute('''
                INSERT INTO friends (name, link, avatar, error)
                VALUES (?, ?, ?, ?);
                ''', (friend['name'], friend['link'], friend['avatar'], friend['error']))
                insert += 1
            else:
                update += 1
        logging.info(f'\n更新 {update} 条友链'
                     f'\n新增 {insert} 条友链')
        conn.commit()
        conn.close()

    def insert_posts(self, posts):
        insert = 0
        update = 0
        conn = self.db_init()
        cursor = conn.cursor()
        for post in posts:
            cursor.execute('''
            UPDATE posts
            SET title = ?, created = ?, updated = ?, author = ?, avatar = ?
            WHERE link = ?;
            ''', (post['title'], post['created'], post['updated'], post['author'], post['avatar'], post['link']))
            if cursor.rowcount == 0:
                cursor.execute('''
                INSERT INTO posts (title, link, created, updated, author, avatar)
                VALUES (?, ?, ?, ?, ?, ?);
                ''', (post['title'], post['link'], post['created'], post['updated'], post['author'], post['avatar']))
                insert += 1
            else:
                update += 1
        logging.info(f'\n更新 {update} 篇文章'
                     f'\n新增 {insert} 篇文章')
        conn.commit()
        conn.close()

    def statistic(self):
        conn = self.db_init()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM friends')
        friend_num = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM friends WHERE error=1')
        lost_friends = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) FROM posts')
        article_num = cursor.fetchone()[0]
        return friend_num, lost_friends, article_num

    def outdate_clean(self, days):
        conn = self.db_init()
        cursor = conn.cursor()
        out_date_post = 0
        cursor.execute('SELECT link, updated FROM posts')
        posts = cursor.fetchall()
        for query_item in posts:
            link = query_item['link']
            updated = query_item['updated']
            try:
                query_time = datetime.strptime(updated, r"%Y-%m-%d")
                if (datetime.now() - query_time).days > days:
                    cursor.execute("DELETE FROM posts WHERE link = ?", (link,))
                    out_date_post += 1
            except:
                cursor.execute("DELETE FROM posts WHERE link = ?", (link,))
                out_date_post += 1
        conn.commit()
        conn.close()
        logging.info(f'\n共删除 {out_date_post} 篇文章')
        return out_date_post

db_manager = DBManager()