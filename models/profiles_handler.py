import json


def get_field_name(origin, field):
    return f"{origin}.{field}"


class ProfilesHandler:
    def __init__(self, profile_id, socketio):
        self.profile_id = profile_id
        self.values = {}
        self.socketio = socketio
        self.should_be_emited = False

    def add_entity(self, field, info):
        self.values[field] = {**info, "value": None}

    def add_value(self, origin, field, value):
        field_name = get_field_name(origin, field)
        if self.values.get(field_name) is None:
            return

        self.should_be_emited = True
        self.values[field_name]['value'] = value

    def emit(self, new: bool = False):
        if not new or self.should_be_emited:
            emit_data = list(self.values.values())
            self.socketio.emit(f'profiles/{self.profile_id}', emit_data)
        self.should_be_emited = False

    @classmethod
    def get_from_config(cls, config_filename, socketio):
        with open(config_filename) as profiles_config:
            config = json.loads(profiles_config.read())

        profile_handlers = {}
        for origin_name, fields in config.items():
            if not isinstance(fields, dict):
                raise ChildProcessError(
                    f"Invalid field type for origin {origin_name}. Field should be a dictionary and is {type(fields)}")
            for field_name, profiles in fields.items():
                if not isinstance(profiles, dict):
                    raise ChildProcessError(
                        f"Invalid field type for key {field_name} in origin {origin_name}. Field should be a dictionary and is {type(fields)}")
                for profile_name, info in profiles.items():
                    if not isinstance(info, dict):
                        raise ChildProcessError(
                            f"Invalid field type for profile {profile_name} key {field_name} origin {origin_name}. Field should be a dictionary and is {type(fields)}")
                    profile_handler = profile_handlers.get(profile_name, cls(profile_name, socketio))
                    profile_handler.add_entity(get_field_name(origin_name, field_name), info)
                    profile_handlers[profile_name] = profile_handler
        return list(profile_handlers.values())
