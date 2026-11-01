from flask import Flask, redirect, url_for, render_template
import settings

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/locations')
def locations():
    return render_template('locations.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

@app.route('/receipts')
def receipts():
    return render_template('receipts.html')

@app.route('/login')
def login():
    return redirect(settings.STAFF_PORTAL_URL)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
