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

    def get_db_connection(self):
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        return conn
    
    def sync_friends_and_posts(self, friends):
        """
        同步 friends 表：
        1) 更新已存在朋友；不存在则插入
        2) 找出数据库里但不在 friends 列表中的 name，先删其 posts，再删其 friends 记录
        要求：
        - posts(author) 存朋友的 name
        - SQLite 连接：self.get_db_connection()
        """

        conn = self.get_db_connection()
        cursor = conn.cursor()
        inserts = 0
        updates = 0

        try:
            cursor.execute('BEGIN')

            # 1) 更新/插入
            for friend in friends:
                cursor.execute(
                    '''
                    UPDATE friends
                    SET link = ?, avatar = ?, error = ?
                    WHERE name = ?;
                    ''',
                    (friend['link'], friend['avatar'], friend['error'], friend['name'])
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        '''
                        INSERT INTO friends (name, link, avatar, error)
                        VALUES (?, ?, ?, ?);
                        ''',
                        (friend['name'], friend['link'], friend['avatar'], friend['error'])
                    )
                    inserts += 1
                else:
                    updates += 1

            # 2) 计算需要删除的朋友（数据库存在但不在当前列表）
            names = [f['name'] for f in friends]

            if names:
                placeholders = ','.join(['?'] * len(names))
                cursor.execute(
                    f'''
                    SELECT name FROM friends
                    WHERE name NOT IN ({placeholders});
                    ''',
                    names
                )
            else:
                cursor.execute('SELECT name FROM friends;')

            to_delete = [row[0] for row in cursor.fetchall()]
            deleted_posts = 0
            deleted_friends = 0
            if to_delete:
                placeholders_del = ','.join(['?'] * len(to_delete))

                # 删除这些作者的文章
                cursor.execute(
                    f'''
                    DELETE FROM posts
                    WHERE author IN ({placeholders_del});
                    ''',
                    to_delete
                )
                deleted_posts = cursor.rowcount

                # 删除这些朋友
                cursor.execute(
                    f'''
                    DELETE FROM friends
                    WHERE name IN ({placeholders_del});
                    ''',
                    to_delete
                )
                deleted_friends = cursor.rowcount

            conn.commit()
            logging.info(
                f'\n更新 {updates} 条友链；新增 {inserts} 条友链'
                f'\n删除 {deleted_friends} 位不在名单内的朋友'
                f'\n删除 {deleted_posts} 篇文章'
            )
            return 0
        except Exception as e:
            conn.rollback()
            logging.exception('同步 friends/posts 失败：%s', e)
            return -1
        finally:
            conn.close()

    def insert_posts(self, posts):
        insert = 0
        update = 0
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN")
            for post in posts:
                cursor.execute(
                    '''
                    UPDATE posts
                    SET title = ?, created = ?, updated = ?, author = ?, avatar = ?
                    WHERE link = ?;
                    ''',
                    (post['title'], post['created'], post['updated'],
                    post['author'], post['avatar'], post['link'])
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        '''
                        INSERT INTO posts (title, link, created, updated, author, avatar)
                        VALUES (?, ?, ?, ?, ?, ?);
                        ''',
                        (post['title'], post['link'], post['created'], post['updated'],
                        post['author'], post['avatar'])
                    )
                    insert += 1
                else:
                    update += 1

            conn.commit()
            logging.info(f'\n更新 {update} 篇文章'
                        f'\n新增 {insert} 篇文章')
            return 0
        except Exception as e:
            conn.rollback()
            logging.exception("插入/更新文章失败，已回滚: %s", e)
            return -1
        finally:
            conn.close()

    def statistic(self):
        """
        返回统计信息：
        - friend_num: friends 总数
        - lost_friends: 所有 error=1 的朋友记录
        - article_num: posts 总数
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN")
            cursor.execute('SELECT COUNT(*) FROM friends')
            friend_num = cursor.fetchone()[0]

            cursor.execute('SELECT * FROM friends WHERE error=1')
            lost_friends = cursor.fetchall()

            cursor.execute('SELECT COUNT(*) FROM posts')
            article_num = cursor.fetchone()[0]

            conn.commit()
            return friend_num, lost_friends, article_num
        except Exception as e:
            conn.rollback()
            logging.exception('统计数据失败，已回滚: %s', e)
            return 0, [], 0
        finally:
            conn.close()

    def outdate_clean(self, days):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        out_date_post = 0
        try:
            cursor.execute("BEGIN")
            cursor.execute('SELECT id, updated FROM posts')
            posts = cursor.fetchall()

            for query_item in posts:
                id_ = query_item['id']
                updated = query_item['updated']
                try:
                    update_time = datetime.strptime(updated, r"%Y-%m-%d")
                    if (datetime.now() - update_time).days > days:
                        cursor.execute("DELETE FROM posts WHERE id = ?", (id_,))
                        out_date_post += 1
                except Exception:
                    # updated 解析失败，直接删
                    cursor.execute("DELETE FROM posts WHERE id = ?", (id_,))
                    out_date_post += 1

            conn.commit()
            logging.info(f'\n删除 {out_date_post} 篇文章')
            return 0

        except Exception as e:
            conn.rollback()
            logging.exception("清理过期文章失败，已回滚: %s", e)
            return -1
        finally:
            conn.close()
    
    def update_friends_status(self):
        """
        根据 posts(author) 统计结果，更新 friends.error：
        - 若该作者无文章：error = 1
        - 否则：error = 0
        整体放入事务，失败回滚；不抛异常，返回 True/False 表示结果。
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN")
            cursor.execute('SELECT id, name FROM friends')
            friends = cursor.fetchall()

            for friend_id, friend_name in friends:
                cursor.execute('SELECT COUNT(*) FROM posts WHERE author = ?', (friend_name,))
                post_count = cursor.fetchone()[0]
                if post_count == 0:
                    cursor.execute('UPDATE friends SET error = 1 WHERE id = ?', (friend_id,))
                else:
                    cursor.execute('UPDATE friends SET error = 0 WHERE id = ?', (friend_id,))

            conn.commit()
            return 0
        except Exception as e:
            conn.rollback()
            logging.exception('更新 friends 状态失败，已回滚: %s', e)
            return -1
        finally:
            conn.close()

db_manager = DBManager()