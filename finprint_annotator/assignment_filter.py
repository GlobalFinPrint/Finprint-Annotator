
class AssignmentFilterDTO(object):
    '''Kept default filter Id as -1 for all filters except for checkBox
    persisting data in form of dictionary which will have id and name of filter applied in previous serach operation'''

    INSTANCE = None

    def __init__(self, trip_filter={"id":-1,"name":"--- Filter by Trip ---"}, reef_filter={"id":-1,"name":"--- Filter by Reef ---"}, set_filter={"id":-1,"name":"--- Filter by Set ---"},
                 anno_filter={"id":-1,"name":"--- Filter by Annotator ---"}, status_filter={"id":-1,"name":"--- Filter by Status ---"},
                 affiliation_filter={"id":-1,"name":"--- Affiliation ---"}, limit_search={"id": 2}):
        if self.INSTANCE is None:
            self._trip_filter = trip_filter
            self._reef_filter = reef_filter
            self._set_filter = set_filter
            self._anno_filter = anno_filter
            self._status_filter = status_filter
            self._affiliation_filter = affiliation_filter
            self._limit_search = limit_search

    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = AssignmentFilterDTO()
        return cls.INSTANCE


    def setFilterValues(self,trip_filter={"id":-1,"name":"--- Filter by Trip ---"}, reef_filter={"id":-1,"name":"--- Filter by Reef ---"}, set_filter={"id":-1,"name":"--- Filter by Set ---"}, anno_filter={"id":-1,"name":"--- Filter by Annotator ---"}, status_filter={"id":-1,"name":"--- Filter by Status ---"},
                        affiliation_filter={"id":-1,"name":"--- Affiliation ---"}, _limit_search={"id": 2}):
        '''assigning the prev filter which user had used for searching'''
        self._trip_filter = trip_filter
        self._set_filter = set_filter
        self._reef_filter = reef_filter
        self._anno_filter = anno_filter
        self._status_filter = status_filter
        self._affiliation_filter = affiliation_filter
        self._limit_search = _limit_search


    def get_trip_filter(self):
        return  self._trip_filter

    def get_reef_filter(self):
        return  self._reef_filter

    def get_set_filter(self):
        return self._set_filter

    def get_anno_filter(self):
        return self._anno_filter

    def get_status_filter(self):
        return self._status_filter

    def get_affiliation_filter(self):
        return self._affiliation_filter

    def get_limit_search(self):
        return self._limit_search