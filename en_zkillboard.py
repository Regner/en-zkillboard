

import os
import json
import logging
import requests

from time import sleep
from gcloud import datastore, pubsub
from gcloud.exceptions import BadRequest

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


def format_notification_subtitle(killmail):
    ship = killmail['package']['killmail']['victim']['shipType']['name']
    solar_system = killmail['package']['killmail']['solarSystem']['name']
    value = '{0:,} ISK'.format(killmail['package']['zkb']['totalValue'])
    
    try:
        name = killmail['package']['killmail']['victim']['character']['name']
        return '{} just lost a {} worth {} in {}.'.format(name, ship, value, solar_system)
        
    except KeyError:
        return 'A {} worth {} just blew up in {}.'.format(ship, value, solar_system)


def format_notification_url(killmail):
    return 'https://zkillboard.com/kill/{}/'.format(killmail['package']['killID'])


def prepare_notifications(killmail, topics):
    topics_per_chunk = 80
    topic_chunks = [topics[x:x + topics_per_chunk] for x in xrange(0, len(topics), topics_per_chunk)]
    
    subtitle = format_notification_subtitle(killmail)
    url = format_notification_url(killmail)
    
    for chunk in topic_chunks:
        send_notification(chunk, subtitle, url)

def send_notification(topics, subtitle, url):
    topics = json.dumps(topics)
    
    try:
        PS_TOPIC.publish(
            '',
            title='zKillboard',
            subtitle=subtitle,
            url=url,
            service='en-zkillboard',
            topics=topics,
        )
    
    except BadRequest as e:
        logger.error(
            'Bad request when trying to send notification. Subtitle: "{}" Url: "{}" Topics: "{}" Error: {}.'.format(
                subtitle,
                url,
                topics,
                e
            )
        )


def get_topics():
    response = requests.get(EN_TOPIC_SETTINGS)
    response.raise_for_status()

    return response.json()['zkillboard']['topics']


def get_from_dict(map_list, data_dict):
    try:
        return reduce(lambda d, k: d[k], map_list, data_dict)
    except KeyError:
        return None


def process_list(entries_list, topic):
    values = []
    
    for entry in entries_list:
        values = values + process_dict(entry, topic)
    
    return values


def process_dict(entry_dict, topic):
    values = []
    
    for key in topic['keys']:
        value = get_from_dict(key, entry_dict)
        
        if value is not None:
            values.append(value)
    
    return values
    

def create_topic_string(topic, value):
    return topic.replace('<int>', str(value))


def convert_values_to_topics(topic, values):
    topic_strings = []
    
    for value in values:
        topic_strings.append(create_topic_string(topic['topic'], value))
    
    return topic_strings


def process_killmail(killmail):
    topics = get_topics()
    topic_strings = []
    
    logger.info('Processing killmail {}.'.format(killmail['package']['killmail']['killID']))
    
    for topic in topics:
        entry = get_from_dict(topic['path'], killmail)
        
        if isinstance(entry, list):
            values = process_list(entry, topic)
        
        elif isinstance(entry, dict):
            values = process_dict(entry, topic)
        
        else:
            logger.error('Topic "{}" path didn\'t resolve to a dict or list.'.format(topic['name']))
            continue
        
        topic_strings = topic_strings + convert_values_to_topics(topic, values)
    
    prepare_notifications(killmail, topic_strings)


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
