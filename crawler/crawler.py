import feedparser
import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from func_timeout import func_set_timeout
from func_timeout.exceptions import FunctionTimedOut
from config import CONFIG
from database.utils import db_manager
feedparser.USER_AGENT = CONFIG['User-Agent']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class Crawler:
    def __init__(self):
        self.headers = {'User-Agent': CONFIG['User-Agent']}

    def get_friends(self, friend_page_config):
        friends = []
        try: 
            url = friend_page_config['link']
            selectors = friend_page_config['info_selectors']
            res = requests.get(url, headers=self.headers)
            res.encoding = 'utf-8'
            parsed = BeautifulSoup(res.text, 'lxml')
            items = parsed.select(selectors['item'])
            for item in items:
                def get_value(rule):
                    try:
                        if 'attr' in rule:
                            return item.select_one(rule['selector']).get(rule['attr'])
                        else:
                            return item.select_one(rule['selector']).text
                    except Exception:
                        return None
                name = get_value(selectors['name'])
                link = get_value(selectors['link'])
                avatar = get_value(selectors['avatar'])
                feed = get_value(selectors['feed'])
                error = True
                if feed:
                    error = False
                friends.append({
                    'name': name,
                    'link': link,
                    'avatar': avatar,
                    'feed': feed,
                    'error': error
                })
            return friends
        except Exception:
            return friends
    
    @func_set_timeout(10)
    def _get_posts(self, friend_info):
        posts = []
        if not friend_info['feed']:
            return []
        feed_url = friend_info['feed']
        max_posts = CONFIG['max_posts_per_friend']
        feeds = feedparser.parse(feed_url)
        entries = feeds['entries']
        status = feeds['status']
        if status != 200:
            return []
        for entry in entries[:max_posts]:
            title = entry['title']
            link = entry['link']
            avatar = friend_info['avatar']
            author = friend_info['name']
            if (datetime.now() - datetime(*entry['updated_parsed'][:6])).days > CONFIG['OUTDATE_CLEAN']:
                continue
            created = time.strftime(r'%Y-%m-%d', entry['published_parsed'])
            updated = time.strftime(r'%Y-%m-%d', entry['updated_parsed'])
            post = {
                'title': title,
                'link': link,
                'avatar': avatar,
                'author': author,
                'created': created,
                'updated': updated
            }
            posts.append(post)
            logging.info(f'\nAuthor: {author}\n'
                        f'Link: {link}\n'
                        f'Title: {title}\n'
                        f'Created: {created}\n'
                        f'Updated: {updated}\n' + '-' * 70)
        return posts

    def get_posts(self, friend_info):
        try:
            return self._get_posts(friend_info)
        except FunctionTimedOut:
            return []
        except Exception:
            return []
