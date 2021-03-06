import boto3
import tweepy

from config import get_config

#Hashtags a serem buscadas
TRACK = ['#cloud, #container, #devops, #aws, #microservices, #docker, #openstack, #automation, #gcp, #azure, #istio, #sre']

# Chaves de acesso da API do Twitter
consumer_key = get_config('TWITTER_CONSUMER_KEY')
consumer_secret = get_config('TWITTER_CONSUMER_SECRET')
access_token = get_config('TWITTER_ACCESS_TOKEN')
access_token_secret = get_config('TWITTER_ACCESS_SECRET')

# Configurações do dynamodb, criado na AWS
session = boto3.Session(region_name='us-east-2',
                        aws_access_key_id=get_config('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=get_config('AWS_SECRET_ACCESS_KEY'))
ddb = session.resource('dynamodb')
table = ddb.Table('runTwitter')


class DynamoStreamListener(tweepy.StreamListener):
    """ A listener that continuously receives tweets and stores them in a
        DynamoDB database.
    """
    def __init__(self, api, table):
        super(tweepy.StreamListener, self).__init__()
        self.api = api
        self.table = table

    def on_status(self, status):

        data = status._json

        content = {}
        content['tweet_id'] = data['id']
        content['timestamp'] = int(data['timestamp_ms'])
        content['lang'] = data['lang']
        content['n_retweets'] = data['retweet_count']
        content['hastags'] = [
            x['text'] for x in data['entities']['hashtags'] if x['text']]
        content['user_mentions'] = [
            x['name'] for x in data['entities']['user_mentions'] if x['name']]
        content['urls'] = [x['url'] for x in data['entities']['urls'] if x['url']]
        content['text'] = data['text']
        content['user_id'] = data['user']['id']
        content['user_name'] = data['user']['name']
        content['coordinates'] = data['coordinates']

        print(content['text'] + '\n')

        try:
            self.table.put_item(Item=content)
        except Exception as e:
            print(str(e))

    def on_error(self, status_code):
        print('Encountered error with status code: {}'.format(status_code))
        return True  # Don't kill the stream

    def on_timeout(self):
        print('Timeout...')
        return True  # Don't kill the stream


def main():
    # Connect to Twitter streaming API
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    # Instantiate DynamoStreamListener and pass it as argument to the stream
    sapi = tweepy.streaming.Stream(auth, DynamoStreamListener(api, table))
    # Get tweets that match one of the tracked terms
    sapi.filter(track=TRACK)

if __name__ == '__main__':
    main()

