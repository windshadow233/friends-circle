from multiprocessing import Pool
from database.utils import db_manager
from database.db_api import *
from crawler.crawler import *


if __name__ == '__main__':
    db_manager.create_db()
    ######################### Fetch Friend URLs ###############################
    crawler = Crawler()
    pool = Pool()
    output = pool.map_async(crawler.get_friends, CONFIG['friend_pages']).get()
    friends = [_ for a in output for _ in a]
    output = pool.map_async(crawler.get_posts, friends).get()
    for posts, friend in zip(output, friends):
        if not posts:
            friend['error'] = True

    posts = [_ for a in output for _ in a]

    ############################ DB Management ################################
    db_manager.insert_friends(friends)
    db_manager.insert_posts(posts)
    out_date_post = db_manager.outdate_clean(CONFIG['OUTDATE_CLEAN'])
    logging.info(f'\n共删除{out_date_post}篇文章')
    friend_num, lost_friends, article_num = db_manager.statistic()
    logging.info(f'\n友链数: {friend_num}'
                 f'\n失联、不活跃友链数: {len(lost_friends)}'
                 f'\n文章总数: {article_num}')
    for lost_friend in lost_friends:
        logging.info(f'失联、不活跃友链: {lost_friend["link"]}')