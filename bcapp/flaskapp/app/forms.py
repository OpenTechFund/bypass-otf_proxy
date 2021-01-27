from wtforms import (StringField, TextAreaField, SubmitField, 
                     BooleanField, SelectField, SelectMultipleField,
                     FileField, widgets)
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length

class UserForm(FlaskForm):
    name = StringField('Name')
    email = StringField('Email Address')
    active = BooleanField('Active?')
    admin = BooleanField('Admin?')
    domain_group_id = SelectField('Domain Group', coerce=int)
    submit = SubmitField('Submit')
