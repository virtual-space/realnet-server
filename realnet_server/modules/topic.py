from .default import Default

class Topic(Default):
    
    def perform_search(self, id, account, data, public=False):
        return []


