

import os
import json
import logging
import requests

from time import sleep
from gcloud import datastore, pubsub

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# App Settings
EN_TOPIC_SETTINGS = os.environ.get('EN_TOPIC_SETTINGS', 'http://en-topic-settings:80/external')
ZKILLBOARD_REDISQ = os.environ.get('ZKILLBOARD_REDISQ', 'http://redisq.zkillboard.com/listen.php')

# PubSub Settings
PS_CLIENT = pubsub.Client()
PS_TOPIC = PS_CLIENT.topic(os.environ.get('NOTIFICATION_TOPIC', 'send_notification'))

if not PS_TOPIC.exists():
    PS_TOPIC.create()


def send_notification(title, subtitle, topics):
    topics = json.dumps(topics)
    
    PS_TOPIC.publish(
        '',
        title=title,
        subtitle=subtitle,
        service='en-zkillboard',
        topics=topics,
    )


def get_topics():
    response = requests.get(EN_TOPIC_SETTINGS)
    response.raise_for_status()

    return response.json()['zkillboard']['topics']


def get_from_dict(map_list, data_dict):
    return reduce(lambda d, k: d[k], map_list, data_dict)


def process_killmail(killmail):
    topics = get_topics()
    
    for topic in topics:
        entry = get_from_dict(topic['path'], killmail)
        logger.info(entry)


while True:
    response = requests.get(ZKILLBOARD_REDISQ)
    
    if response.status_code == requests.codes.ok:
        killmail = response.json()
        
        if killmail['package'] is not None:
            process_killmail(killmail)
        
        else:
            logger.info('No new killmail.')
    
    else:
        logger.error('Problem with zKB response. Got code {}.'.format(response.status_code))
