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
        ## Warning... initializing private attributes here will override values with

    def login(self, user_name, pwd):
        data = {'username': user_name, 'password': pwd}
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
        r = requests.post(self.address + '/api/logout', {'token': self.user_token})
        return r.status_code == 200

    def set_list(self):
        r = requests.get(self.address + '/api/set', params={'token': self.user_token})
        return r.json()

    def set_detail(self, set_id):
        r = requests.get(self.address + '/api/set/{0}'.format(set_id), params={'token': self.user_token})
        return r.json()

    def mark_set_done(self, set_id):
        r = requests.post(self.address + '/api/set/{0}/done'.format(set_id), {'token': self.user_token})
        return r.status_code == 200

    def observations(self, set_id):
        r = requests.get(self.address + '/api/set/{0}/obs'.format(set_id), params={'token': self.user_token})
        return r.json()

    def add_observation(self, set_id, observation):
        r = requests.post(self.address + '/api/set/' + set_id + '/obs', {'observation' : observation, 'token': self.user_token})
        if r.status_code == 200:
            return r.json()

    def delete_observation(self, set_id, observation):
        r = requests.delete(self.address + '/api/set/' + set_id + '/obs',  {'observation' : observation, 'token': self.user_token})
        if r.status_code == 200:
            return r.json()

    def critters(self, set_id):
        r = requests.get(self.address + '/api/set/' + set.id + '/critters', params={'token': self.user_token})
        return r.json

