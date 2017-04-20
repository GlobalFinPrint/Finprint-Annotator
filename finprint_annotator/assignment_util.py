
class AssignmentFilter():
    def __init__(self,_trip_filter_index=0, _set_filter_index=0, _anno_filter_index=0, _status_filter_index=0,
                 _affiliation_filter_index=0, _limit_search_index=2):
        self._trip_filter_index = _trip_filter_index
        self._set_filter_index = _set_filter_index
        self._anno_filter_index = _anno_filter_index
        self._status_filter_index = _status_filter_index
        self._affiliation_filter_index = _affiliation_filter_index
        self._limit_search_index = _limit_search_index


    def setFilterValues(self,_trip_filter_index=0, _set_filter_index=0, _anno_filter_index=0, _status_filter_index=0,
                        _affiliation_filter_index=0, _limit_search_index=2):
        '''assigning the prev filter which user had used for searching'''
        self._trip_filter_index =_trip_filter_index
        self._set_filter_index = _set_filter_index
        self._anno_filter_index = _anno_filter_index
        self._status_filter_index =_status_filter_index
        self._affiliation_filter_index =_affiliation_filter_index
        self._limit_search_index = _limit_search_index
