from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import datetime
from hashlib import md5

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)


# Index
@app.route('/')
def index():
    return render_template('home.html')


# About
@app.route('/about')
def about():
    return render_template('about.html')


# Articles
@app.route('/articles')
def articles():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    # Close connection
    cur.close()


#Single Article
@app.route('/article/<string:id>/')
def article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    return render_template('article.html', article=article)


# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get care centers
    # Show care centers only from the user logged in 
    result = cur.execute("SELECT * FROM in_network WHERE author = %s", [session['username']])

    care_centers = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', care_centers=care_centers)
    else:
        msg = 'No Centers Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",
            (title, body, session['username']))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Article Created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)


# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()
    cur.close()
    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(title)
        # Execute
        cur.execute ("UPDATE articles SET title=%s, body=%s WHERE id=%s",(title, body, id))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))


'''
################################################################
                Begin Care Center addition
################################################################
'''

# Care Centers
@app.route('/care_centers')
@is_logged_in
def care_centers():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get care centers
    result = cur.execute("SELECT * FROM in_network")

    care_centers = cur.fetchall()

    if result > 0:
        return render_template('care_centers.html', care_centers=care_centers)
    else:
        msg = 'No Care Centers Found'
        return render_template('care_centers.html', msg=msg)
    # Close connection
    cur.close()

#Single Care Center
@app.route('/care_center/<string:id>/')
def care_center(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article
    cur.execute("SELECT * FROM in_network WHERE ID = %s", [id])

    care_center = cur.fetchone()

    return render_template('care_center.html', care_centers=care_center)


# Care center class
class CareCenterForm(Form):
    center_name = StringField('name', [validators.Length(min=1, max=100)])
    center_address = StringField('address', [validators.Length(min=10)])
    center_phone = StringField('phone', [validators.Length(min=6)])

# Add urgent care center/hospital
@app.route('/add_care_center', methods=['GET', 'POST'])
@is_logged_in
def add_hospital():
    form = CareCenterForm(request.form)

    if request.method == 'POST' and form.validate():
        center_name = form.center_name.data
        center_address = form.center_address.data
        center_phone = form.center_phone.data

        cur = mysql.connection.cursor()
        
        cur.execute('INSERT INTO in_network(name, address, phone, author) VALUES(%s, %s, %s, %s)', (center_name, center_address, center_phone, session['username']))

        mysql.connection.commit()

        cur.close()

        # Show an on-screen message and redirect to dashboard. 
        flash('Care center added', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_care_center.html', form=form)


# Edit Care center
@app.route('/edit_care_center/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_care_center(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    cur.execute("SELECT * FROM in_network WHERE ID = %s", [id])

    care_centers = cur.fetchone()
    cur.close()

    # Get form
    form = CareCenterForm(request.form)

    # Populate article form fields
    form.center_name.data = care_centers['name']
    form.center_address.data = care_centers['address']
    form.center_phone.data = care_centers['phone']

    if request.method == 'POST' and form.validate():
        center_name = request.form['center_name']
        center_address = request.form['center_address']
        center_phone = request.form['center_phone']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(center_name)

        # Execute
        cur.execute ("UPDATE in_network SET name=%s, address=%s, phone=%s WHERE ID=%s", (center_name, center_address, center_phone, id))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Care center updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_care_center.html', form=form)


if __name__ == '__main__':
    app.secret_key = md5((datetime(1988,4,28,0,0).strftime('%s').encode('utf-8'))).hexdigest()
    app.run(debug=True)
