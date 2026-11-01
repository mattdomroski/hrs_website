from flask import Flask, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return 'This is the home page'

@app.route('/about')
def about():
    return 'This is the about page'

@app.route('/contact')
def contact():
    return 'This is the contact page'

@app.route('/locations')
def locations():
    return 'This is the locations page'

@app.route('/receipts')
def receipts():
    return 'This is the receipts page'

@app.route('/login')
def login():
    return 'This is the staff login page (will redirect to staff portal)'

if __name__ == '__main__':
    app.run(debug=True, port=5001)
