from flask import Flask
app = Flask(__name__)

# pip install python-dotenv
import dotenv, os
dotenv.load_dotenv()

@app.route('/')
def hello_world():
    return '''
        <h1>Hello World!!!</h1>
        <p><a href="/about">About the site</a>
        <p><button onclick='alert("button clicked"); window.location.href="/about"'>About the site</button>
        '''

@app.route('/about')
def about():
    return '''
        <h2>About</h2>
        <p>This is a website for Research Algorithms course.
        <p><a href="/">Back to homepage</a>
        '''

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("FLASK_RUN_PORT"))
