from .animal import Animal
from .extent import Extent

class Observation(object):
    def __init__(self):
        self.id = None
        self.initial_observation_time = 0
        self.animal_id = None
        self.behavior_id = None
        self.comment = ''
        self.duration = 0
        self.animal = Animal()
        self.type_choice = 'A'
        self.extent = Extent()

    def load(self, obs_dict):
        self.type_choice = obs_dict['type_choice']
        self.id = obs_dict['id']
        self.comment = obs_dict['comment']
        self.initial_observation_time = int(obs_dict['initial_observation_time'])
        self.duration = obs_dict['duration']
        if 'extent' in obs_dict and obs_dict['extent']:
            self.extent.from_wkt(obs_dict['extent'])

        if self.type_choice == 'A':
            self.animal_id = obs_dict['animal_id']

    def to_dict(self):
        return {'id': self.id,
                'initial_observation_time': self.initial_observation_time,
                'animal_id': self.animal_id,
                'type_choice': self.type_choice,
                'type': self.type_choice,  # TODO band-aid till the backend gets fixed
                'comment': self.comment,
                'duration': self.duration,
                'extent': self.extent.to_wkt() if not self.extent.empty else None}

    def to_columns(self):
        return [
            self.id,
            self.type_choice,
            self.initial_observation_time,
            str(self.animal),
            self.duration,
            self.comment
        ]
