from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField, SelectField


class EditGroupForm(FlaskForm):
    description = StringField('Description')
    submit = SubmitField('Save Changes')


class EditOriginForm(FlaskForm):
    domain_name = StringField('Domain Name')
    description = StringField('Description')
    group = SelectField('Group')
    submit = SubmitField('Save Changes')


class EditMirrorForm(FlaskForm):
    origin = SelectField('Origin')
    url = StringField('URL')
    submit = SubmitField('Save Changes')


class EditProxyForm(FlaskForm):
    origin = SelectField('Origin')
    submit = SubmitField('Save Changes')


class LifecycleForm(FlaskForm):
    submit = SubmitField('Confirm')
