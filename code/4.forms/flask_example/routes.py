# Here, we import the forms, since they are used for routing.
# We also add routing to the registration and the login pages.

from flask import render_template, url_for, flash, redirect
from flask_example import app
from flask_example.forms import DataForm, LoginForm


@app.route('/')
def myhome():
    return render_template('home.html', username=myhome.username, homepage=myhome.homepage)
myhome.username = "Anonymous"
myhome.homepage = None

def password_is_valid(username,password):
    return password=="123"

@app.route('/login', methods=['GET', 'POST'])
def loginform():
    form = LoginForm()
    is_submitted = form.validate_on_submit()
        # This is True if the user has submitted a valid form.
        # This is False when the user enters this page for the first time,
        #      or when the user has submitted an invalid form.
    if not is_submitted:
        return render_template('login.html', form=form)
    else:
        if password_is_valid(form.username.data, form.password.data):
            flash(f'Welcome, {form.username.data}!', 'success')
            myhome.username = form.username.data
        else:
            flash(f'Wrong password, {form.username.data}!', 'danger')
        return redirect(url_for(myhome.__name__))

@app.route("/data", methods=['GET', 'POST'])
def data():
    form = DataForm()
    if not form.validate_on_submit():
        return render_template('data.html', title='Data', form=form)
    else:
        myhome.homepage = form.homepage.data
        return redirect(url_for(myhome.__name__))
