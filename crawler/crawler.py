import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timedelta
from func_timeout import func_set_timeout
from func_timeout.exceptions import FunctionTimedOut
from config import *
feedparser.USER_AGENT = CONFIG['User-Agent']



class Crawler:
    def __init__(self):
        self.headers = {'User-Agent': CONFIG['User-Agent']}

    @staticmethod
    def replace_hostname(url, old_hostname, new_hostname):
        parsed_url = urlparse(url)
        new_netloc = parsed_url.netloc.replace(old_hostname, new_hostname)
        new_url = urlunparse(parsed_url._replace(netloc=new_netloc))
        return new_url

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
                friends.append({
                    'name': name,
                    'link': link,
                    'avatar': avatar,
                    'feed': feed,
                    'error': False
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
        success_num = 0
        for entry in entries:
            title = entry['title']
            link = entry['link']
            avatar = friend_info['avatar']
            author = friend_info['name']
            created = datetime(*entry['published_parsed'][:6]) + timedelta(hours=8)
            updated = datetime(*entry['updated_parsed'][:6]) + timedelta(hours=8)
            if (datetime.now() - updated).days > CONFIG['OUTDATE_CLEAN']:
                continue
            if author in CONFIG['url_replace']:
                link = self.replace_hostname(link, CONFIG['url_replace'][author]['old'], CONFIG['url_replace'][author]['new'])
            post = {
                'title': title,
                'link': link,
                'avatar': avatar,
                'author': author,
                'created': created.strftime(r'%Y-%m-%d'),
                'updated': updated.strftime(r'%Y-%m-%d')
            }
            posts.append(post)
            logging.info(f'\nAuthor: {author}\n'
                        f'Link: {link}\n'
                        f'Title: {title}\n'
                        f'Created: {created}\n'
                        f'Updated: {updated}\n' + '-' * 70)
            success_num += 1
            if success_num >= max_posts:
                break
        return posts

    def get_posts(self, friend_info):
        try:
            return self._get_posts(friend_info)
        except FunctionTimedOut:
            return []
        except Exception:
            return []
