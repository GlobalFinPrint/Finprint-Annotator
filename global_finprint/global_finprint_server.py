import requests


class Singleton:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class QueryException(Exception):
    pass


class GlobalFinPrintServer(Singleton):
    def __init__(self):
        Singleton.__init__(self)

        # Warning... Do not initialize private attributes after it's been instantiated.
        if not hasattr(self, 'instantiated'):
            self.instantiated = True
            self.logged_in = False
            self.user_token = None
            self.user_role = None
            self.user_name = ''
            self.user_id = None
            self.address = None

    def is_lead(self):
        return self.user_role == 'lead'

    def is_assigned_to_self(self, set):
        return self.user_id == set.assigned_to['id']

    def login(self, user_name, pwd, server):
        data = {'username': user_name, 'password': pwd}
        self.address = server
        r = requests.post(self.address + '/api/login', data)
        self.logged_in = False
        if r.status_code == 200:
            self.logged_in = True
            data = r.json()
            self.user_token = data['token']
            self.user_role = data['role']
            self.user_name = user_name
            self.user_id = data['user_id']
        elif r.status_code == 403:
            raise QueryException('Unknown user or user not assigned to proper role')
        else:
            raise QueryException('Unknown status code ' + r.status_code)

        return self.logged_in, data

    def logout(self):
        r = requests.post(self.address + '/api/logout', {'token': self.user_token})
        self.logged_in = not r.status_code == 200
        return not self.logged_in

    def set_list(self, **kwargs):
        params = {'token': self.user_token}
        params.update(kwargs)
        r = requests.get(self.address + '/api/set', params=params)
        return r.json()

    def trip_list(self):
        r = requests.get(self.address + '/api/trip', params={'token': self.user_token, 'assigned': True})
        return r.json()

    def annotator_list(self):
        r = requests.get(self.address + '/api/annotator', params={'token': self.user_token})
        return r.json()

    def set_detail(self, set_id):
        r = requests.get(self.address + '/api/set/{0}'.format(set_id), params={'token': self.user_token})
        return r.json()

    def mark_set_done(self, set_id):
        r = requests.post(self.address + '/api/set/{0}/done'.format(set_id), {'token': self.user_token})
        return r.status_code == 200

    def update_progress(self, set_id, progress):
        r = requests.post(self.address + '/api/set/{0}/progress'.format(set_id),
                          {'token': self.user_token, 'progress': int(progress)})
        return r.status_code == 200

    def observations(self, set_id):
        r = requests.get(self.address + '/api/set/{0}/obs'.format(set_id), params={'token': self.user_token})
        return r.json()

    def add_observation(self, set_id, **kwargs):
        data = kwargs  # TODO make sure first event stuff is in here
        data['token'] = self.user_token
        r = requests.post(self.address + '/api/set/{0}/obs'.format(set_id), data=data)
        if r.status_code == 200:
            return r.json()
        else:
            raise QueryException('Failed to add Observation: status {0}'.format(r.status_code))

    def edit_observation(self, set_id, obs_id, **kwargs):
        data = kwargs  # TODO make sure event stuff ISNT here
        data['token'] = self.user_token
        r = requests.post(self.address + '/api/set/{0}/obs/{1}'.format(set_id, obs_id), data)
        if r.status_code == 200:
            return r.json()
        else:
            raise QueryException('Failed to update Observation: status {0}'.format(r.status_code))

    def delete_observation(self, set_id, obs_id):
        params = {'obs_id': obs_id, 'token': self.user_token}
        r = requests.delete(self.address + '/api/set/{0}/obs'.format(set_id), params=params)
        if r.status_code == 200:
            return r.json()
        else:
            raise QueryException('Failed to delete observation: status {0}'.format(r.status_code))

    def add_event(self, set_id, obs_id, **kwargs):
        params = {'token': self.user_token}
        params.update(kwargs)  # TODO filter out non-event stuff?
        r = requests.post(self.address + '/api/set/{0}/obs/{1}/event'.format(set_id, obs_id), params)
        if r.status_code == 200:
            return r.json()
        else:
            raise QueryException('Failed to add event: status {0}'.format(r.status_code))

    def edit_event(self, set_id, obs_id, evt_id, **kwargs):
        params = {'token': self.user_token}
        params.update(kwargs)  # TODO filter out non-event stuff?
        r = requests.post(self.address + '/api/set/{0}/obs/{1}/event/{2}'.format(set_id, obs_id, evt_id), params)
        if r.status_code == 200:
            return r.json()
        else:
            raise QueryException('Failed to edit event: status {0}'.format(r.status_code))

    def delete_event(self, set_id, obs_id, evt_id):
        params = {'token': self.user_token, 'evt_id': evt_id}
        r = requests.delete(self.address + '/api/set/{0}/obs/{1}/event'.format(set_id, obs_id), params=params)
        if r.status_code == 200:
            return r.json()
        else:
            raise QueryException('Failed to delete event: status {0}'.format(r.status_code))

    def attributes(self, set_id):
        params = {'token': self.user_token}
        r = requests.get(self.address + '/api/set/{0}/attributes'.format(set_id), params)
        if r.status_code == 200:
            return r.json()['attributes']
        else:
            raise QueryException('Failed to get attributes: status {0}'.format(r.status_code))

    def animals(self, set_id):
        r = requests.get(self.address + '/api/set/{0}/animals'.format(set_id), params={'token': self.user_token})
        return r.json
