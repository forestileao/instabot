from time import time as tm
import requests

class InstaBot:
    def __init__(self, username='mff.tester', password='MhG6reYKyK4C2PC'):
        self.username = username
        self.password = password
        self.base_url = 'https://www.instagram.com'
    

    def login(self):
        login_url = self.base_url + '/accounts/login/ajax/'
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)\
            Chrome/59.0.3071.115 Safari/537.36'

        #Setting some headers and refers
        session = requests.Session()
        session.headers = {'user-agent': user_agent}
        session.headers.update({'Referer': self.base_url})


        try:
            #Requesting the base url. Grabbing and inserting the csrftoken

            req = session.get(self.base_url)
            session.headers.update({'x-csrftoken': req.cookies['csrftoken']})
            login_data = {'username': self.username, 'encpassword':'#PWD_INSTAGRAM_BROWSER:10:' + str(int(tm())) + ':' + self.password}

            #Finally login in
            login = session.post(login_url, data=login_data, allow_redirects=True)
            session.headers.update({'x-csrftoken': login.cookies['csrftoken']})

            cookies = login.cookies

            #Print the html results after I've logged in
            print(login.text)

        #In case of refused connection
        except requests.exceptions.ConnectionError:
            print("Connection refused")


if __name__ == "__main__":
    bot = InstaBot()
    bot.login()
