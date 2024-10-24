import json
import os
import signal


def get_field_name(origin, field):
    return f"{origin}.{field}"


class ProfilesHandler:
    def __init__(self, profile_id, socketio):
        self.profile_id = profile_id
        self.values = {}
        self.socketio = socketio
        self.should_be_emited = False

    def add_entities(self, field, info):
        self.values[field] = [{**element, "value": None} for element in info]

    def add_value(self, origin, field, value):
        field_name = get_field_name(origin, field)
        entities = self.values.get(field_name)
        if entities is None:
            return

        self.should_be_emited = True
        entities = [{**entity, 'value': value} for entity in entities]
        self.values[field_name] = entities

    def emit(self, new: bool = False):
        if not new or self.should_be_emited:
            emit_data = []
            for element in self.values.values():
                emit_data.extend(element)
            self.socketio.emit(f'profiles/{self.profile_id}', emit_data)
        self.should_be_emited = False

    @classmethod
    def get_from_config(cls, config_filename, socketio, profile_handlers=None):

        print(f"reading profiles config {config_filename}")
        with open(config_filename) as profiles_config:
            config = json.loads(profiles_config.read())

        imports = config.pop('imports', [])

        for filename in imports:
            if not os.path.isfile(filename):
                print(f"import {filename} in cofig {config_filename} not found, quitting")
                os.kill(os.getpid(), signal.SIGINT)
                return

            if filename==config_filename:
                print(f"infinite import {filename} found, quitting")
                os.kill(os.getpid(), signal.SIGINT)
                return
            profile_handlers = cls.get_from_config(filename, socketio, profile_handlers)
        if profile_handlers is None:
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
                    if isinstance(info, dict):
                        info = [info, ]

                    for i, value in enumerate(info):
                        if not isinstance(value, dict):
                            raise ChildProcessError(
                                f"Invalid field type for profile {profile_name} key {field_name} origin {origin_name} value {i + 1}. Field should be a dictionary and is {type(fields)}")
                    profile_handler = profile_handlers.get(profile_name, cls(profile_name, socketio))

                    profile_handler.add_entities(get_field_name(origin_name, field_name), info)
                    profile_handlers[profile_name] = profile_handler

        return profile_handlers


    @classmethod
    def get_handlers(cls, initial_config_filename, socketio):
        try:
            handlers = cls.get_from_config(initial_config_filename, socketio)
            return list(handlers.values())
        except Exception as e:
            print(f'failed to create profiles handler: {e}, quitting')
            os.kill(os.getpid(), signal.SIGINT)
            return []