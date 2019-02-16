import mongoengine as me


class User(me.Document):
    name = me.StringField(max_length=40, required=True)
    user_id = me.StringField(max_length=200, required=True)
    karma = me.IntField()
