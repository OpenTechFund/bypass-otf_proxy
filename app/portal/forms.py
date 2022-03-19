from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired


class NewGroupForm(FlaskForm):
    group_name = StringField("Short Name", validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired()])
    eotk = BooleanField("Deploy EOTK instances?")
    submit = SubmitField('Save Changes', render_kw={"class": "btn btn-success"})


class EditGroupForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired()])
    eotk = BooleanField("Deploy EOTK instances?")
    submit = SubmitField('Save Changes', render_kw={"class": "btn btn-success"})


class NewOriginForm(FlaskForm):
    domain_name = StringField('Domain Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    group = SelectField('Group', validators=[DataRequired()])
    submit = SubmitField('Save Changes')


class EditOriginForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired()])
    group = SelectField('Group', validators=[DataRequired()])
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
