from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, InputRequired, NumberRange, URL, Regexp
from wtforms.widgets import TextArea

class LoginForm(FlaskForm):
    username = StringField(label='Username', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[Length(min=2, max=18)])
    remember = BooleanField(label='Remember Me')
    submit = SubmitField(label='Submit')


class DataForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    age = IntegerField("Age", validators=[InputRequired(), NumberRange(0,120)])
    homepage = StringField("Homepage", validators=[DataRequired(), Regexp("https?://.*")])
    description = TextAreaField('Description', widget=TextArea())
    language = SelectField(u'Language', choices=[('he', 'Hebrew'), ('en', 'English'), ('fr', 'French')])
    submit = SubmitField('Compute')

