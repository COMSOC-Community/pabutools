from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField
from wtforms.validators import InputRequired

class QuadraticFormulaForm(FlaskForm):
    a = IntegerField("a", validators=[InputRequired()])
    b = IntegerField("b", validators=[InputRequired()])
    c = IntegerField("c", validators=[InputRequired()])
    submit = SubmitField('Compute')
