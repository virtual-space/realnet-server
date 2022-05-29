def cleanup_type(type):
    result = dict()
    
    id = type.get('id')
    if id:
        result['id'] = id

    name = type.get('name')
    if name:
        result['name'] = name

    attributes = type.get('attributes')
    if attributes:
        result['attributes'] = attributes

    icon = type.get('icon')
    if icon:
        result['icon'] = icon

    base = type.get('base')
    if base:
        result['base'] = cleanup_type(base)

    return result

def cleanup_item(item):
    result = dict()
    
    id = item.get('id')
    if id:
        result['id'] = id

    name = item.get('name')
    if name:
        result['name'] = name

    location = item.get('location')
    if location:
        result['location'] = location

    valid_from = item.get('valid_from')
    if valid_from:
        result['valid_from'] = valid_from

    valid_to = item.get('valid_to')
    if valid_to:
        result['valid_to'] = valid_to

    status = item.get('status')
    if status:
        result['status'] = status

    attributes = item.get('attributes')
    if attributes:
        result['attributes'] = attributes

    type = item.get('type')
    if type:
        result['type'] = cleanup_type(type)

    # items = item.get('items')
    # if items:
    #    result['items'] = [cleanup_item(i) for i in items]

    return result