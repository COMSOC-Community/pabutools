from flask import Flask, render_template
app = Flask(__name__)

import dotenv, os
dotenv.load_dotenv()  # load FLASK_RUN_PORT

@app.route('/')
def hello_world():
    return render_template('home.html') # from the "templates" folder

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("FLASK_RUN_PORT"))

