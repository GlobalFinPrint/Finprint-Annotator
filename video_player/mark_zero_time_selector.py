

MARK_ZERO_TIME_GLOBAL_ID = 16

class MarkZeroTimeSelector :
    '''
    extracts primary id of mark zero using global parent id of mark zero
    '''
    def __init__(self, attributes):
        self._attributes = attributes

    def get_mark_zero_time_attr(self):
        '''
        get local mark zero time id to be saved while saving observation or an event
        '''
        _list_of_tags = []
        for attr in self._attributes:
            if 'children' in attr:
                for child in attr['children']:
                    if child['global_parent_id'] == MARK_ZERO_TIME_GLOBAL_ID:
                        _list_of_tags.append(child)
            else:
                if attr['global_parent_id'] == MARK_ZERO_TIME_GLOBAL_ID:
                    _list_of_tags.append(attr)

        if _list_of_tags :
             return _list_of_tags[0]
        else :
             print(" Global parent id for Mark Zero Time not found!!1")

