from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Regexp

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=2, max=20)])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Submit')


class DataForm(FlaskForm):
    homepage = StringField("Homepage", validators=[DataRequired(), Regexp("https?://.*")])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])    
    submit = SubmitField('Submit')

