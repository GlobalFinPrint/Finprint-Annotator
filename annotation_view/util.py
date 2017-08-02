from math import floor
from enum import IntEnum
from PyQt4.QtCore import *

def convert_position(pos):
    s, m = divmod(floor(pos), 1000)
    h, s = divmod(s, 60)
    pos = "{0:02}:{1:02}:{2:03}".format(h, s, m)
    return pos


class ColumnsEnum(IntEnum):
    event_time = 0
    id = 1
    type = 2
    annotator = 3
    organism = 4
    observation_comment = 5
    duration = 6
    frame_capture = 7
    event_notes = 8
    attributes = 9

class ObservationColumn :
  @staticmethod
  def return_observation_table_coloumn_details() :
     return ['Time',
             'ID',
             'Type',
             'Annotator',
             'Organism',
             'Observation Note',
             'Duration',
             'Frame capture',
             'Image notes',
             'Tags']

class MultiKeyPressHandler:

    def aggregate_key_event(self, key_pressed):
        return sum(key_pressed)

    def process_multi_key_press(self, obj):
        aggregate_key_events = self.aggregate_key_event(obj.keylist)
        if aggregate_key_events == Qt.Key_Shift + Qt.Key_Left:
            obj.on_step_back()
        elif aggregate_key_events == Qt.Key_Shift + Qt.Key_Right:
            obj.on_step_forward()
        elif aggregate_key_events == Qt.Key_Control + Qt.Key_Left:
            obj.on_back05()
        elif aggregate_key_events == Qt.Key_Control + Qt.Key_Down:
            obj.on_back15()


