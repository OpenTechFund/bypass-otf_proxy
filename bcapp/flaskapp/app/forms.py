from wtforms import (StringField, TextAreaField, SubmitField, 
                     BooleanField, SelectField, SelectMultipleField,
                     FileField, widgets)
from flask_wtf import FlaskForm
from wtforms.fields.simple import HiddenField
from wtforms.validators import DataRequired, Length

class UserForm(FlaskForm):
    name = StringField('Name')
    email = StringField('Email Address')
    active = BooleanField('Active?')
    admin = BooleanField('Admin?')
    notifications = BooleanField('Get Notifications?')
    password = StringField('New Password')
    domain_group_id = SelectField('Domain Group', coerce=int)
    user_bio = TextAreaField('Bio')
    submit = SubmitField('Edit User')

class DomainForm(FlaskForm):
    domain = StringField('Domain')
    old_domain = HiddenField('Old Domain')
    ext_ignore = StringField('Extensions to ignore')
    paths_ignore = StringField('Paths to ignore')
    s3_storage_bucket = StringField('S3 Storage Bucket')
    azure_profile_name = StringField('Azure Profile Name')
    inactive = BooleanField('Inactive?')
    submit = SubmitField('Edit Domain')

class DomainGroupForm(FlaskForm):
    name = StringField('Name')
    notes = TextAreaField('Notes')
    submit = SubmitField('Submit')

class AltForm(FlaskForm):
    mirror_type = SelectField('Mirror Type', choices=[
        ('mirror', 'Mirror'),
        ('proxy', 'Cloudfront, AzureEdge or Fastly'),
        ('eotk', 'Onion'),
        ('ipfs', 'IPFS Node')])
    mirror_url = StringField('Alternative URL')
    inactive = BooleanField('Inactive?')
    domain_id = HiddenField('Domain ID')
    old_url = HiddenField('Old Url')
    submit = SubmitField('Submit')
