import json
import time
from os import path
from threading import Thread
from time import sleep

import requests


BASE_URL = 'https://www.instagram.com'
USER_AGENT = (
    'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36'
)

FOLLOWERS_QUERY_HASH = 'c76146de99bb02f6415203be841dd25a'
FOLLOWING_QUERY_HASH = 'd04b0a864b4b54837c0d870b0e77e076'
SUGGESTED_QUERY_HASH = 'ed2e3ff5ae8b96717476b62ef06ed8cc'

FOLLOWERS_PAGE_SIZE = 24
FOLLOWERS_NEXT_PAGE_SIZE = 12
FOLLOWING_PAGE_SIZE = 24

RATE_LIMIT_PREFIX = 'Ple'
RATE_LIMIT_WAIT_SECONDS = 10 * 60
SUGGESTED_ERROR_WAIT_SECONDS = 3 * 60
INSTAGRAM_DESCRIPTION_PREFIX = 'Ins'

SUGGESTED_QUERY = {
    'fetch_media_count': 0,
    'fetch_suggested_count': 30,
    'ignore_cache': True,
    'filter_followed_friends': True,
    'seen_ids': [],
    'include_reel': True,
}


class InstaBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = BASE_URL

    def get_userid(self, username):
        url = f'https://instagram.com/{username}/?__a=1'
        response = self.session.get(url)
        if response.status_code != 200:
            return None
        payload = json.loads(response.content.decode('utf-8'))
        return payload['graphql']['user']['id']

    def generate_encrypted_password(self):
        timestamp = str(int(time.time()))
        return f'#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{self.password}'

    def login(self):
        login_url = self.base_url + '/accounts/login/ajax/'
        self.session = requests.Session()
        self.session.headers = {'user-agent': USER_AGENT}
        self.session.headers.update({'Referer': self.base_url})
        enc_password = self.generate_encrypted_password()

        try:
            home = self.session.get(self.base_url)
            self._set_csrf(home)
            login_data = {'username': self.username, 'enc_password': enc_password}
            login = self.session.post(login_url, data=login_data, allow_redirects=True)
            self._set_csrf(login)
            login = json.loads(login.content.decode('utf-8'))

            if login['authenticated']:
                self.user_id = login['userId']
                print(f'> Logged in (user:{self.username}, id:{self.user_id})')
            else:
                print('> Erron on login authentication')
                print(login)
            return login
        except requests.exceptions.ConnectionError:
            print('> Connection refused')

    def map_user_followers(self, username, limit=1000):
        print(f'*** Mapping {limit} followers from {username}***')
        self.user_followers = []
        self.user_foll_num = int(0)
        user_id = self.get_userid(username)
        count = 0
        cursor = ''

        while True:
            if count == 0:
                foll_url = self._connection_url(
                    FOLLOWERS_QUERY_HASH,
                    user_id,
                    first=FOLLOWERS_PAGE_SIZE,
                    fetch_mutual=True,
                )
                foll_req_list = self._get_json(foll_url)
                self.user_foll_num = foll_req_list['data']['user']['edge_followed_by']['count']
            else:
                foll_url = self._connection_url(
                    FOLLOWERS_QUERY_HASH,
                    user_id,
                    first=FOLLOWERS_NEXT_PAGE_SIZE,
                    fetch_mutual=False,
                    cursor=cursor,
                )
                foll_req_list = self._get_json(foll_url)

            if foll_req_list['status'] == 'fail':
                break

            foll_req_list = foll_req_list['data']['user']['edge_followed_by']
            for user in foll_req_list['edges']:
                if self.verbose:
                    print(f'> {user["node"]["username"]} added to target followers list')
                self.user_followers.append(self._user_record(user['node']))
                count += 1

            cursor = foll_req_list['page_info']['end_cursor']
            if count == limit:
                self._write_cache('target-followers.json', self.followers)
                break

    def map_followers(self):
        print('*** Mapping followers ***')
        self.followers = []
        self.foll_num = int(0)
        count = 0
        cursor = ''

        while True:
            if count == 0:
                foll_url = self._connection_url(
                    FOLLOWERS_QUERY_HASH,
                    self.user_id,
                    first=FOLLOWERS_PAGE_SIZE,
                    fetch_mutual=True,
                )
                foll_req_list = self._get_json(foll_url)
                self.foll_num = int(foll_req_list['data']['user']['edge_followed_by']['count'])
            else:
                foll_url = self._connection_url(
                    FOLLOWERS_QUERY_HASH,
                    self.user_id,
                    first=FOLLOWERS_NEXT_PAGE_SIZE,
                    fetch_mutual=False,
                    cursor=cursor,
                )
                foll_req_list = self._get_json(foll_url)

            if foll_req_list['status'] == 'fail':
                break

            foll_req_list = foll_req_list['data']['user']['edge_followed_by']
            for user in foll_req_list['edges']:
                self.followers.append(self._user_record(user['node']))
                count += 1
                if self.verbose:
                    print('>', user['node']['username'], 'added to follower list')

            cursor = foll_req_list['page_info']['end_cursor']
            if count == self.foll_num:
                self._write_cache('followers.json', self.followers)
                break

    def map_following(self):
        print('*** Mapping people who you are following ***')
        self.following = []
        count = 0
        cursor = ''

        while True:
            if count == 0:
                foll_url = self._connection_url(
                    FOLLOWING_QUERY_HASH,
                    self.user_id,
                    first=FOLLOWING_PAGE_SIZE,
                    fetch_mutual=True,
                )
                foll_req_list = self._get_json(foll_url)
                self.following_num = foll_req_list['data']['user']['edge_follow']['count']
            else:
                foll_url = self._connection_url(
                    FOLLOWING_QUERY_HASH,
                    self.user_id,
                    first=FOLLOWING_PAGE_SIZE,
                    fetch_mutual=False,
                    cursor=cursor,
                )
                foll_req_list = self._get_json(foll_url)

            if foll_req_list['status'] == 'fail':
                break

            edge = foll_req_list['data']['user']['edge_follow']
            for user in edge['edges']:
                self.following.append(self._user_record(user['node']))
                count += 1
                if self.verbose:
                    print('>', user['node']['username'], 'added to list of people you are following')

            cursor = edge['page_info']['end_cursor']
            if count == self.following_num:
                self._write_cache('following.json', self.following)
                break

    def follow_user(self, userid):
        return self._friendship_action(userid, 'follow')

    def unfollow_user(self, userid):
        return self._friendship_action(userid, 'unfollow')

    def get_suggested_followers(self):
        url = (
            self.base_url
            + '/graphql/query/?query_hash='
            + SUGGESTED_QUERY_HASH
            + '&variables='
            + json.dumps(SUGGESTED_QUERY)
        )
        response = self.session.get(url)
        if response.status_code != 200:
            return None

        print('> Getting Suggested')
        payload = json.loads(response.content.decode('utf-8'))
        print(payload['status'])
        return self._suggested_users(payload)

    def just_follow(self):
        if not self.other_user:
            self.map_followers()
            while self.foll_num < self.hoped_foll or self.other_user:
                self._follow_batch(self.get_suggested_followers)
        else:
            self.map_user_followers(username=self.target_username)
            while self.user_foll_num < self.hoped_foll or self.other_user:
                self._follow_batch(lambda: self.user_followers)

    def just_unfollow(self):
        self.map_followers()
        self.map_following()
        while self.following_num > self.foll_num or self.unfollow_all_not_followers:
            print('[*] Followers:', self.foll_num)
            print('[*] Following:', self.following_num)
            self._unfollow_non_followers()
            self.map_followers()
            self.map_following()

    def start(self, target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False):
        self.unfollow_all_not_followers = unfollow_all_not_followers
        self.other_user = False
        self.verbose = verbose

        if len(target_username) > 0:
            self.target_username = target_username
            self.other_user = True

        self.hoped_foll = hoped_foll
        self.login()

        Thread(target=self.just_follow).start()
        Thread(target=self.just_unfollow).start()

    def _set_csrf(self, response):
        self.session.headers.update({'x-csrftoken': response.cookies['csrftoken']})

    def _get_json(self, url):
        response = self.session.get(url)
        return json.loads(response.content.decode('utf-8'))

    def _connection_url(self, query_hash, user_id, first, fetch_mutual, cursor=None):
        mutual = 'true' if fetch_mutual else 'false'
        variables = f'"id":"{user_id}","include_reel":true,"fetch_mutual":{mutual},"first":{first}'
        if cursor is not None:
            variables += f',"after":"{cursor}"'
        return self.base_url + '/graphql/query/?query_hash=' + query_hash + '&variables={' + variables + '}'

    def _user_record(self, node):
        return {'username': node['username'], 'id': node['id']}

    def _write_cache(self, filename, payload):
        cache_path = path.dirname(__file__) + '/../cache/' + filename
        with open(cache_path, 'w') as outfile:
            json.dump(payload, outfile)

    def _friendship_action(self, userid, action):
        url = self.base_url + f'/web/friendships/{userid}/{action}/'
        response = self.session.post(url)
        print('[' + str(response.status_code) + ']', end='')
        body = response.content.decode('utf-8')
        if body[:3] == RATE_LIMIT_PREFIX or response.status_code != 200:
            return False
        return True

    def _suggested_users(self, payload):
        suggested = []
        for foll in payload['data']['user']['edge_suggested_users']['edges']:
            if foll['node']['description'][:3] == INSTAGRAM_DESCRIPTION_PREFIX:
                continue
            suggested.append({
                'username': foll['node']['user']['username'],
                'id': foll['node']['user']['id'],
            })
        return suggested

    def _follow_batch(self, users_provider):
        print('*** Following Users ***')
        try:
            for user in users_provider():
                self._follow_one(user)
        except:
            print('> Error in suggested')
            sleep(SUGGESTED_ERROR_WAIT_SECONDS)

    def _follow_one(self, user):
        if self.follow_user(user['id']):
            print(f'> Followed {user["username"]}')
        else:
            print('> Waiting 10 min until next FOLLOW request')
            sleep(RATE_LIMIT_WAIT_SECONDS)

    def _unfollow_non_followers(self):
        for following in self.following:
            count = 1
            if count >= 50:
                break
            if {'username': following['username'], 'id': following['id']} in self.followers:
                count += 1
                continue
            self._unfollow_until_success(following)

    def _unfollow_until_success(self, following):
        while not self.unfollow_user(following['id']):
            print('> Waiting 10 minutes until next UNFOLLOW request.')
            sleep(RATE_LIMIT_WAIT_SECONDS)
        print(f'> Unfollowed {following["username"]}')
