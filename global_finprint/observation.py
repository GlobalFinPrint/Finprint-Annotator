from .animal import Animal
from .extent import Extent
from math import floor
from datetime import datetime


# TODO figure out why this won't import form annotation_view.util
def convert_position(pos):
    s, m = divmod(floor(pos), 1000)
    h, s = divmod(s, 60)
    return "{0:02}:{1:02}:{2:03}".format(h, s, m)


class Event(object):
    def __init__(self):
        self.id = None
        self.event_time = None
        self.attribute = []
        self.note = None
        self.extent = Extent()
        self.observation = None
        self.create_datetime = None
        self.max_n = None

    def load(self, evt_dict, obs):
        self.id = evt_dict['id']
        self.event_time = evt_dict['event_time']
        self.attribute = evt_dict['attribute']
        # adding new column in observation table
        if 'measurables' in evt_dict and evt_dict['measurables']:
            self.flag = True
            for measurable in evt_dict['measurables'] :
                if self.flag and measurable['measurable_name'] == 'MaxN' :
                    self.max_n = measurable['value']
                    self.flag = False

        else :
            self.max_n=''

        self.note = evt_dict['note']
        if 'extent' in evt_dict:
            self.extent.from_wkt(evt_dict['extent'])
        self.create_datetime = datetime.strptime(evt_dict['create_datetime'], '%Y-%m-%d %H:%M:%S')
        self.observation = obs

    def to_dict(self):
        return {
            'id': self.id,
            'event_time': self.event_time,
            'attribute': self.attribute,
            'note': self.note,
            'extent': self.extent.to_wkt(),
            'max_n': self.max_n
        }

    def to_columns(self):
        return [
            self.id,
            'event',
            self.event_time,
            ', '.join(list(a['name'] for a in self.attribute)),
            None,  # placeholder
            self.note
        ]

    def to_table_columns(self):
        return [
            convert_position(self.event_time),
            self.observation.id,
            self.observation.type_choice,
            'TODO Annotator',
            str(self.observation.animal),
            ', '.join([a['name'] for a in self.attribute]),
            str(self.max_n),
            self.observation.comment,
            self.observation.duration,
            'TODO frame capture',  # just keep empty for now
            self.note

        ]

    def __str__(self):
        return '{0}'.format(convert_position(self.event_time))


class Observation(object):
    def __init__(self):
        self.id = None
        self.animal_id = None
        self.behavior_id = None
        self.comment = ''
        self.duration = 0
        self.animal = Animal()
        self.type_choice = 'A'
        self.events = []

    def initial_time(self):
        return sorted(self.events, key=lambda x: x.create_datetime)[0].event_time

    def load(self, obs_dict):
        self.type_choice = obs_dict['type_choice']
        self.id = obs_dict['id']
        self.comment = obs_dict['comment']
        self.duration = obs_dict['duration']
        for e in obs_dict['events']:
            evt = Event()
            evt.load(e, self)
            self.events.append(evt)
        if self.type_choice == 'A':
            self.animal_id = obs_dict['animal_id']

    def to_dict(self):
        return {'id': self.id,
                'animal_id': self.animal_id,
                'type_choice': self.type_choice,
                'comment': self.comment,
                'duration': self.duration,
                'events': list(e.to_dict() for e in self.events)}

    def to_columns(self):
        return [
            self.id,
            self.type_choice,
            self.initial_time(),
            str(self.animal),
            self.duration,
            self.comment
        ]

    def __str__(self):
        return '{0} {1} ({2} events)'.format(convert_position(self.initial_time()),
                                             'Non-animal observation' if self.type_choice == 'I' else str(self.animal),
                                             len(self.events))