# Here, we import the forms, since they are used for routing.

from flask import render_template, url_for, flash, redirect
from flask_example import app
from flask_example.forms import QuadraticFormulaForm
from flask_example import quadratic
from io import StringIO
import logging


@app.route('/', methods=['GET', 'POST'])
def quadraticform():
    form = QuadraticFormulaForm()
    is_submitted = form.validate_on_submit()
    if not is_submitted:
        return render_template('quadratic.html', form=form)
    else:
        a, b, c = form.a.data, form.b.data, form.c.data
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: Line %(lineno)d: %(message)s')
        log_handler.setFormatter(formatter)
        quadratic.logger.addHandler(log_handler)
        quadratic.logger.setLevel(logging.DEBUG)
        roots = quadratic.quadratic_formula(a, b, c)
        quadratic.logger.removeHandler(log_handler)
        logs = log_stream.getvalue()
        return render_template('quadratic_result.html', a=a, b=b, c=c, roots=roots, logs=logs)
