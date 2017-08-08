from math import floor
from enum import IntEnum


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


