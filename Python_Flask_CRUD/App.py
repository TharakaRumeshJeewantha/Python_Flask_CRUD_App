from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL

app = Flask(__name__)

app.secret_key = "flash message"

# database connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'python'

mysql = MySQL(app)

# routes
# route initial
@app.route('/')
def Index():

    # read data (Fetch Data)
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM tbl_users")
    fetch_data = cursor.fetchall()
    cursor.close()

    return render_template('index.html', users=fetch_data)

# route inserting data
@app.route('/insert', methods = ['POST'])
def insert():
    if request.method == "POST":

        flash("New user created successfully")

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        telephone = request.form['telephone']

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO tbl_users (first_name, last_name, email, telephone) VALUES (%s, %s, %s, %s)", (first_name, last_name, email, telephone))
        mysql.connection.commit()
        return redirect(url_for('Index'))

# route updating data
@app.route('/update', methods = ['POST', 'GET'])
def update():
    if request.method == 'POST':

        flash("User updated successfully")

        u_id = request.form['id']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        telephone = request.form['telephone']

        cursor = mysql.connection.cursor()
        cursor.execute("""
        UPDATE tbl_users
        SET 
        first_name = %s,
        last_name = %s,
        email = %s,
        telephone = %s
        WHERE id = %s
        """, (first_name, last_name, email, telephone, u_id))

        mysql.connection.commit()
        return redirect(url_for('Index'))

# route deleting data
@app.route('/delete/<string:u_id>', methods = ['POST', 'GET'])
def delete(u_id):

    flash("User deleted successfully")

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM tbl_users WHERE id = %s", (u_id))
    mysql.connection.commit()
    return redirect(url_for('Index'))


# server
if __name__ == "__main__":
    app.run(debug=True)