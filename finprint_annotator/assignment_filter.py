
class AssignmentFilterDTO(object):
    INSTANCE = None

    def __init__(self,trip_filter_index=0, set_filter_index=0, anno_filter_index=0, status_filter_index=0,
                 affiliation_filter_index=0, limit_search_index=2):
        if self.INSTANCE is None:
            self._trip_filter_index = trip_filter_index
            self._set_filter_index = set_filter_index
            self._anno_filter_index = anno_filter_index
            self._status_filter_index = status_filter_index
            self._affiliation_filter_index = affiliation_filter_index
            self._limit_search_index = limit_search_index

    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = AssignmentFilterDTO()
        return cls.INSTANCE


    def setFilterValues(self,trip_filter_index=0, set_filter_index=0, anno_filter_index=0, status_filter_index=0,
                        affiliation_filter_index=0, limit_search_index=2):
        '''assigning the prev filter which user had used for searching'''
        self._trip_filter_index = trip_filter_index
        self._set_filter_index = set_filter_index
        self._anno_filter_index = anno_filter_index
        self._status_filter_index = status_filter_index
        self._affiliation_filter_index = affiliation_filter_index
        self._limit_search_index = limit_search_index


    def get_trip_filter_index(self):
        return  self._trip_filter_index

    def get_set_filter_index(self):
        return self._set_filter_index

    def get_anno_filter_index(self):
        return self._anno_filter_index

    def get_status_filter_index(self):
        return self._status_filter_index

    def get_affiliation_filter_index(self):
        return self._affiliation_filter_index

    def get_limit_search_index(self):
        return self._limit_search_index