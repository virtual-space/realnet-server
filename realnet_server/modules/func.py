from .default import Default

class Func(Default):

    def create_item(self, parent_item=None, **kwargs):
        func = parent_item
        if func:
            code = func.attributes.code
            if code:
                result = dict()
                safe_list = ['func', 'arguments', 'result']
                safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
                eval(func.code, None, safe_dict)
                return result
        else:
            return None


