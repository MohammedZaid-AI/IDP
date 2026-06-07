import json

def validate_json(data):

    try:

        obj = json.loads(data)

        if len(obj.keys()) == 0:

            return False

        return True

    except:

        return False