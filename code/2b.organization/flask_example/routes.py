from flask import render_template
from flask_example import app


users = [
    {'name': 'Joee Javany',
    'email': 'joo@example.com',
    'phone': '111-1111'},
    {'name': 'Tom Pythonovitch',
    'email': 'python_is_coool@example.com',
    'phone': '222-2222'},
    {'name': 'abc',
    'email': 'xyz',
    'phone': '123'},
]

@app.route('/')
def myhome():
    return render_template('home.html')
