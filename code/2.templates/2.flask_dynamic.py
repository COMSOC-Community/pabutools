from flask import Flask, render_template
app = Flask(__name__)

import dotenv, os
dotenv.load_dotenv()  # load FLASK_RUN_PORT

users_from_database = [   # Simulates reading from database.
    {'name': 'Joee Javany',
    'email': 'joo@example.com',
    'phone': '111-1111'},
    {'name': 'Tom Pythonovitch',
    'email': 'python_is_coool@example.com',
    'phone': '333-3333'},
    {'name': 'Tami CPP',
    'email': 'cpp-forever@example.com',
    'phone': '222-2222'},
    {'name': 'Rusty Rust',
    'email': 'rust@example.com',
    'phone': '5555555'},
    {'name': 'A B C',
    'email': 'abc@example.com',
    'phone': '123123'},
]

@app.route('/')
def hello_world():
    return render_template('homedynamic.html', users=users_from_database)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("FLASK_RUN_PORT"))
