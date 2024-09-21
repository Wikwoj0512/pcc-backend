import json


def get_field_name(origin, field):
    return f"{origin}.{field}"


class ProfilesHandler:
    def __init__(self, profiles_config_filename, socketio):
        self.fields = []
        self.values = {}
        self.entities = {}
        self.socketio = socketio
        if self.read_config(profiles_config_filename) is None:
            raise ChildProcessError
        self.should_be_emited = True

    def read_config(self, profiles_config_filename):
        try:
            with open(profiles_config_filename) as profiles_config:
                config = json.load(profiles_config)
            for element in config:
                origin = element.get('origin', None)
                field = element.get('field', None)
                if origin is None or field is None:
                    print(f"failed parsing profiles config element {element}")

                field_name = get_field_name(origin, field)
                self.fields.append(field_name)
                element.pop('origin', None)
                element.pop('field', None)
                self.entities[field_name] = element
            return self
        except Exception as e:
            print(f"failed parsing profiles config: {e}")
            return None

    def add_value(self, origin, field, value):
        filed_name = get_field_name(origin, field)
        if filed_name not in self.fields:
            return

        self.values[filed_name] = value
        self.should_be_emited = True

    def prepare_emit_data(self):
        emit_data = []
        for field in self.fields:
            value = self.values.get(field)
            entity = self.entities.get(field)
            if entity is None:
                continue
            new_entity = {**entity, 'value': value}
            emit_data.append(new_entity)
        return emit_data

    def emit_new(self):
        if self.should_be_emited:
            self.emit()
        self.should_be_emited = False

    def emit(self):
        emit_data = self.prepare_emit_data()
        self.socketio.emit('profiles/raw', emit_data)
