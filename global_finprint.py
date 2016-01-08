from config import global_config
import requests


class Singleton:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class GlobalFinPrintServer(Singleton):
    def __init__(self):
        Singleton.__init__(self)
        self.address = global_config.parser['GLOBAL_FINPRINT_SERVER'].get('address')
        self.user_name = None
        self.user_token = None

    def login(self, user_name, pwd):
        data = {'user': user_name, 'password': pwd}
        r = requests.post(self.address + '/api/login', data)
        success = False
        data = {}
        if r.status_code == 200:
            success = True
            data = r.json()
            self.user_token = data['token']
            self.user_name = user_name
        elif r.status_code == 403:
            data['msg'] = 'Unknown User'
        else:
            data['msg'] = 'Unknown status code ' + r.status_code

        return success, data

    def logout(self):
        r = requests.post(self.address + '/api/logout')
        return r.status_code == 200

    def set_list(self):
        r = requests.get(self.address + '/api/set')
        return r.json()

    def set_detail(self, set_id):
        r = requests.get(self.address + 'api/set/' + set_id)
        return r.json()

    def mark_set_done(self, set_id):
        r = requests.post(self.address + 'api/set/' + set_id + '/done')
        return r.status_code == 200

    def observations(self, set_id):
        r = requests.get(self.address + 'api/set/' + set_id + '/obs')
        return r.json()

    def add_observation(self, set_id, observation):
        r = requests.post(self.address + 'api/set/' + set_id + '/obs', observation)
        if r.status_code == 200:
            return r.json()

    def delete_observation(self, set_id, observation):
        r = requests.post(self.address + 'api/set/' + set_id + '/obs', observation)
        if r.status_code == 200:
            return r.json()

    def critters(self, set_id):
        r = requests.get(self.address + '/api/set/' + set.id + '/critters')
        return r.json

