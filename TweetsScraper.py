####################
## Initialization ##
####################
## Import Libraries and Dependencies
import requests
import datetime as dt
from datetime import date, datetime, timedelta
import json
import time
import random
import sys
import os
import errno
import pandas as pd

from selenium import webdriver
from bs4 import BeautifulSoup

######################
## Path & Variables ##
######################
OUTPUT_PATH = os.getcwd() + "\\output"
STARTDATE = sys.argv[1]
ENDDATE = sys.argv[2]
EVENT = sys.argv[3]
TERM = sys.argv[4]

####################
## Query Function ##
####################
## Initialization ##
ITEMS = {'user':[], 'fullname':[], 'tweet_id':[], 'url':[], 'timestamp':[], 
         'text':[], 'replies':[], 'retweets':[], 'likes':[]}

HEADERS_LIST = ["Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1",
                "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
                "Mozilla/5.0 (Windows; U; Windows NT 6.1; x64; fr; rv:1.9.2.13) Gecko/20101203 Firebird/3.6.13",
                "Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko",
                "Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201",
                "Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16",
                "Mozilla/5.0 (Windows NT 5.2; RW; rv:7.0a1) Gecko/20091211 SeaMonkey/9.23a1pre"]

HEADER = {'User-Agent': random.choice(HEADERS_LIST)}

INIT_URL = "https://twitter.com/search?f=tweets&vertical=default&q={q}&l={lang}"
RELOAD_URL = "https://twitter.com/i/search/timeline?f=tweets&vertical=" \
             "default&include_available_features=1&include_entities=1&" \
             "reset_error_state=false&src=typd&max_position={pos}&q={q}&l={lang}"

def perdelta(start, end, delta):
    curr = start
    while curr < end:
        yield curr
        curr += delta

def query_single_page(url, html_response=True, retry=10):
    
    try:
        response = requests.get(url, headers=HEADER)
        if html_response:
            html = response.text or ''
        else:
            html = ''
            try:
                json_resp = json.loads(response.text)
                html = json_resp['items_html'] or ''
            except ValueError as e:
                print('Failed to parse JSON "{}" while requesting "{}"'.format(e, url))
        
        
        soup = BeautifulSoup(html, "lxml")
        tweets = soup.find_all('li', 'js-stream-item')
        
        if tweets:    
            for tweet in tweets:
                ## AWS TODO
                user = tweet.find('span', 'username').text or ""

                fullname = tweet.find('strong', 'fullname').text or "" 

                tweet_id = tweet['data-item-id'] or ""

                url = tweet.find('div', 'tweet')['data-permalink-path'] or ""

                timestamp = datetime.utcfromtimestamp(int(tweet.find('span', '_timestamp')['data-time']))

                text = tweet.find('p', 'tweet-text').text or ""

                replies = tweet.find('span', 'ProfileTweet-action--reply u-hiddenVisually') \
                    .find('span', 'ProfileTweet-actionCount')['data-tweet-stat-count'] or '0'

                retweets = tweet.find('span', 'ProfileTweet-action--retweet u-hiddenVisually') \
                    .find('span', 'ProfileTweet-actionCount')['data-tweet-stat-count'] or '0'

                likes = tweet.find('span', 'ProfileTweet-action--favorite u-hiddenVisually') \
                    .find('span', 'ProfileTweet-actionCount')['data-tweet-stat-count'] or '0'

                ITEMS['user'].append(user)
                ITEMS['fullname'].append(fullname)
                ITEMS['tweet_id'].append(tweet_id)
                ITEMS['url'].append(url)
                ITEMS['timestamp'].append(timestamp)
                ITEMS['text'].append(text)
                ITEMS['replies'].append(replies)
                ITEMS['retweets'].append(retweets)
                ITEMS['likes'].append(likes)

        if not tweets:
            return [], None

        if not html_response:
            return tweets, json_resp['min_position']
        
        return tweets, "TWEET-{}-{}".format(ITEMS['tweet_id'][-1], ITEMS['tweet_id'][0])
    
    except requests.exceptions.HTTPError as e:
        print('HTTPError {} while requesting "{}"'.format(e, url))
    except requests.exceptions.ConnectionError as e:
        print('ConnectionError {} while requesting "{}"'.format(e, url))
    except requests.exceptions.Timeout as e:
        print('TimeOut {} while requesting "{}"'.format(e, url))
    except json.decoder.JSONDecodeError as e:
        print('Failed to parse JSON "{}" while requesting "{}".'.format(e, url))

    if retry > 0:
        print("Retrying... (Attempts left: {})".format(retry))
        return query_single_page(url, html_response, retry-1)

    print("Giving up.")
    return [], None

def query_tweets(query, lang='en', begindate=dt.date(2006,3,21), enddate=dt.date.today(), limit=None):

    print("Querying {} from {} to {}".format(query, begindate, enddate))
    
    query = query.replace(' ', '%20').replace("#", "%23").replace(":", "%3A")
    pos = None
    tweets = []
    
    queries = ['{} since:{} until:{}'.format(query, begindate, enddate)]

    try:
        while True:
            new_tweets, pos = query_single_page(
                INIT_URL.format(q=queries, lang=lang) if pos is None
                else RELOAD_URL.format(q=queries, pos=pos, lang=lang),
                pos is None
            )
            
            if len(new_tweets) == 0:
                print("Got {} tweets for {}. No more tweets!".format(len(tweets), query))
                return 

            tweets += new_tweets
            print("Got {} new tweets.".format(len(new_tweets)))
                  
            if limit and len(tweets) >= limit:
                print("Got {} tweets for {}. Reach limits!".format(len(tweets), query))
                return 
            
    except KeyboardInterrupt:
        print("Program interrupted by user. Returning tweets gathered so far...")
    except BaseException:
        print("An unknown error occurred! Returning tweets gathered so far.")
    
    print("Got {} tweets for {} on {}.".format(len(tweets), query, begin_date))
    return tweets

##################
## Main Program ##
##################
## Query Tweets ##
begin_date = datetime.strptime(STARTDATE, '%Y%m%d').date()
end_date = datetime.strptime(ENDDATE, '%Y%m%d').date()
# end_date = dt.date.today()
query = TERM
event = EVENT
lang = 'en'

day_list = []
for day in perdelta(begin_date, end_date, timedelta(days=1)):
    day_list.append(day)

for day in day_list:
    ITEMS.clear()
    ITEMS = {'user':[], 'fullname':[], 'tweet_id':[], 'url':[], 'timestamp':[], 
             'text':[], 'replies':[], 'retweets':[], 'likes':[]}
    
    begin_date = day
    end_date = day + timedelta(days=1)
    
    query_tweets(query=query, begindate=begin_date, enddate=end_date)
    
    df = pd.DataFrame.from_dict(ITEMS)
    print("Unique text: {}".format(df['text'].nunique()))
    print("Saving.....")

    filename = OUTPUT_PATH + "\\" + event + "\\"
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    df.to_csv(OUTPUT_PATH + "\\" + event + "\\" + event + " " + str(begin_date) + " to " + str(end_date) + ".csv")

    print("Saved!!")