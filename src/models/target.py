import mongoengine as me


class Target(me.Document):
    name = me.StringField(max_length=40, required=True)
    karma = me.IntField()
