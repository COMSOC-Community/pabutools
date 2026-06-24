# Here, we import the forms, since they are used for routing.
# We also add routing to the registration and the login pages.

from flask import render_template, url_for, flash, redirect
from flask_example import app
from flask_example.forms import DataForm, LoginForm


@app.route('/')
def myhome():
    return render_template('home.html', 
        username=myhome.username, 
        homepage=myhome.homepage, 
        picture=myhome.picture_filename
        )
myhome.username = "Anonymous"
myhome.homepage = None
myhome.picture_filename = None

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
        form.homepage.data = myhome.homepage
        return render_template('data.html', title='Data', form=form)
    else:
        if form.homepage.data:
            myhome.homepage = form.homepage.data
        if form.picture.data:
            myhome.picture_filename = save_picture(form.picture.data)
        return redirect(url_for(myhome.__name__))

import os, pathlib
def save_picture(form_picture_data):
    # random_hex = secrets.token_hex(8)
    # _, f_ext = os.path.splitext(form_picture.filename)
    # picture_filename = random_hex + f_ext
    picture_filename = form_picture_data.filename
    picture_path = os.path.join(app.root_path, 'static/profile_pics')
    pathlib.Path(picture_path).mkdir(parents=True, exist_ok=True)  # create all folders in the given path.
    form_picture_data.save(os.path.join(picture_path, picture_filename))

    # output_size = (125, 125)
    # img_file = Image.open(form_picture)
    # img_file.thumbnail(output_size)
    # img_file.save(picture_path)

    return picture_filename
