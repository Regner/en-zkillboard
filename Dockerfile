

FROM debian:latest
MAINTAINER Regner Blok-Andersen <shadowdf@gmail.com>

ENV GOOGLE_APPLICATION_CREDENTIALS "path-to-credentials.json"
ENV EN_TOPIC_SETTINGS "http://en-topic-settings/external"
ENV ZKILLBOARD_REDISQ "http://redisq.zkillboard.com/listen.php"
ENV NOTIFICATION_TOPIC "send_notification"

ADD en_zkillboard.py /en_zkillboard/
ADD requirements.txt /en_zkillboard/

WORKDIR /en_zkillboard/

RUN apt-get update -qq \
&& apt-get upgrade -y -qq \
&& apt-get install -y -qq python-dev python-pip \
&& apt-get autoremove -y \
&& apt-get clean autoclean \
&& pip install -qU pip \
&& pip install -r requirements.txt

CMD python /en_zkillboard/en_zkillboard.py
