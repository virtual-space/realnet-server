
from .default import Default
import os
import json
import copy


class Filesystem(Default):

    def get_items(self, item):
        items = []
        if os.path.isdir(item['attributes']['path']):
            for f in os.listdir(item['attributes']['path']):
                i = copy.deepcopy(item)
                i['id'] = os.path.join(item['id'], f)
                i['name'] = f
                items.append(i)
        return json.dumps(items)


