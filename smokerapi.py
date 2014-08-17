from flask import Flask
from flask import jsonify
from flask import g
from flask import render_template
from flask import request

from flask_googlelogin import GoogleLogin
from flask_login import login_required, login_user, logout_user
from flask.ext.login import current_user
from flask import redirect,session

from datetime import datetime

from smokerlib import *
from sqlalchemy import desc
import smokerconfig 

import psycopg2

app = Flask(__name__)
app.secret_key = smokerconfig.sessionsecret
app.config["GOOGLE_LOGIN_CLIENT_ID"] = smokerconfig.google_client_id
app.config["GOOGLE_LOGIN_CLIENT_SECRET"] = smokerconfig.google_client_secret
#app.config["GOOGLE_LOGIN_SCOPES"] = ""
app.config["GOOGLE_LOGIN_REDIRECT_URI"] = "https://smoker.culinaryapparatus.com/devapi/oauth2callback"
app.config["GOOGLE_LOGIN_REDIRECT_SCHEME"] = "https"
app.debug = True
googlelogin = GoogleLogin()
googlelogin.init_app(app)

def get_db():
	if not hasattr(g, 'database'):
		g.database = psycopg2.connect("dbname=smoker user=apache")
	return g.database

@app.teardown_appcontext
def close_db(error):
	if hasattr(g,'database'):
		g.database.close()

@app.route('/oauth2callback')
@googlelogin.oauth2callback
def create_or_update_user(token, userinfo, **params):
	db = get_db()
	cursor = db.cursor()
	cursor.execute("select google_id,name,email,administrator,update from users where google_id = %s;",(userinfo["id"],))
	dbval = cursor.fetchone()
	if dbval == None:
		# create user
		cursor.execute("insert into users (google_id,name) VALUES (%(id)s,%(name)s);",userinfo)
	else:
		# update user if required
		if userinfo["name"] != dbval[1] or userinfo["email"] != dbval[2]:
			cursor.execute("update users set name = %(name)s,email = %(email)s where google_id = %(id)s;",userinfo)

	db.commit()
	user = User(userinfo['id'])
	user.name = userinfo['name']
	login_user(user)
	return redirect('/testform.html')

@app.route("/login")
@login_required
def login():
	return redirect('/client/SmokerGraphs.html')

@googlelogin.user_loader
def get_user(userid):
	db = get_db()
	cursor = db.cursor()
	cursor.execute("select google_id,name from users where google_id = %s;",(userid,))
	dbval = cursor.fetchone()

	user = User(dbval[0])
	user.name = dbval[1]
	return user

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return """
        <p>Logged out</p>
        <p><a href="/">Return to /</a></p>
        """
@app.route('/profile')
@login_required
def profile():
	return "Hello %s %s" % (current_user.name,current_user.email)
#@app.route('/')
#def hello_world():
    #return 'Hello World!'

@app.route('/smoker',methods=['GET'])
def list_smokers():
	dbsmokers = Smoker.query.all()

	smokers = []
	for smoker in dbsmokers:
		unit = dict()
		unit['id'] = smoker.id
		unit['name'] = smoker.name
		smokers.append(unit)

	return jsonify(smokers=smokers)

@app.route('/smoker/<int:smoker_id>/io', methods=['GET'])
def list_io(smoker_id):
	db_io = SmokerIO.query.filter(SmokerIO.smoker_id == smoker_id)
	io = []
	for io_dev in db_io:
		io.append(dict(id=io_dev.id,name=io_dev.name,unit=io_dev.unit,unit_abbrev=io_dev.unit_abbrev))

	return jsonify(smoker_io=io)

@app.route('/smoker/<int:smoker_id>/parameters/<paramname>',methods=['POST'])
@login_required
def set_parameter(smoker_id,paramname):
	if request.method == 'POST':
		value = request.form['value']
		io = SmokerIO.query.filter(SmokerIO.smoker_id == smoker_id).filter(SmokerIO.varname == paramname).first()
		v = IOValue(smoker_io_id=io.id,value=value)
		database.db_session.add(v)
		database.db_session.commit()
	return jsonify(return_value=0)

@app.route('/values/<int:smoker_id>/<varname>',methods=['GET'])
def get_io_values(smoker_id,varname):

	starttime = request.args.get('start','')
	interval = request.args.get('interval',15)
	time_interval = int(interval)

	if starttime == '':
		v = IOValue.query.join(IOValue.smoker_io).filter(SmokerIO.smoker_id == smoker_id).filter(SmokerIO.varname == varname).order_by(desc(IOValue.time)).first()	
		return jsonify(time=v.time,value=v.value,units=v.smoker_io.unit_abbrev)
	else:
		start = datetime.strptime(starttime,'%Y%m%d-%H:%M:%S.%f')
		v = IOValue.query.join(IOValue.smoker_io).filter(SmokerIO.smoker_id == smoker_id).filter(SmokerIO.varname == varname).filter(IOValue.time > start).order_by(IOValue.time).all()	
		data = TimeData(v)
		wi = data.weighted_intervals(time_interval)
		return jsonify(result=wi)


@app.route('/smoker/<int:smoker_id>/power/batterycharge',methods=['GET'])
def get_battery_charge(smoker_id):
	v = IOValue.query.join(IOValue.smoker_io).filter(SmokerIO.smoker_id == smoker_id).filter(SmokerIO.varname == 'batvoltage').order_by(desc(IOValue.time)).first()	

	voltage = v.value

	if (voltage > 12.8):
		charge = 100.0
	elif (voltage <= 12.8 and voltage > 12.6):
		charge = (voltage - 12.6) / (12.8 - 12.6) * 25.0 + 75
	elif (voltage <= 12.6 and voltage > 12.3):
		charge = (voltage - 12.3) / (12.6 - 12.3) * 25.0 + 50
	elif (voltage <= 12.3 and voltage > 12.0):
		charge = (voltage - 12.0) / (12.3 - 12.0) * 25.0 + 25
	elif (voltage <= 12.0 and voltage > 11.8):
		charge = (voltage - 11.8) / (12.0 - 11.8) * 25.0 
	else:
		charge = 0

	return jsonify(time=v.time,value=charge,units='%')

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0",port=8000)
