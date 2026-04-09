from marshmallow import Schema, fields, validates, ValidationError
from werkzeug.datastructures import FileStorage

class RequestSchema(Schema):
    text = fields.String(required=True, metadata={"description": "Il messaggio del cliente"})

class ResponseSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True, dump_only=True)
    category = fields.Str(required=True, dump_only=True)
    priority = fields.Str(required=True, dump_only=True)
    suggested_reply = fields.Str(required=True, dump_only=True)
    status = fields.Str(required=True, dump_only=True)
    extracted_data = fields.Str(required=True, dump_only=True)
    feedback = fields.Str(required=True, dump_only=True)
    created_at = fields.DateTime(required=True, dump_only=True)

class FileField(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, FileStorage):
            raise ValidationError("Deve essere un file.")
        return value

class RequestFotoSchema(Schema):
    file = FileField(required=True)
    richiesta = fields.Str()


class FotoResponseSchema(Schema):
    id = fields.Int(dump_only=True)
    foto_path = fields.Str(required=True, dump_only=True)
    razza = fields.Str(required=True, dump_only=True)
    famiglia = fields.Str(required=True, dump_only=True)
    descrizione = fields.Str(required=True, dump_only=True)
    pericolosità = fields.Str(required=True, dump_only=True)
    classificazione = fields.Str(required=True, dump_only=True)

    status = fields.Str(required=True, dump_only=True) 
    created_at = fields.DateTime(required=True, dump_only=True)

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    create_at = fields.DateTime(dump_only=True)
    modify_at = fields.DateTime(dump_only=True)

class UserLoginSchema(UserSchema):
    username = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)

class UserRegisterSchema(UserLoginSchema):
    email = fields.Str(required=True)

