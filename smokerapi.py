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
import smokerconfig 

import psycopg2

app = Flask(__name__)
app.secret_key = smokerconfig.sessionsecret
app.config["GOOGLE_LOGIN_CLIENT_ID"] = smokerconfig.google_client_id
app.config["GOOGLE_LOGIN_CLIENT_SECRET"] = smokerconfig.google_client_secret
app.config["GOOGLE_LOGIN_SCOPES"] = "https://www.googleapis.com/auth/plus.login"
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
	user = User(userinfo['id'])
	user.name = userinfo['name']
	login_user(user)
	return redirect('/')

@googlelogin.user_loader
def get_user(userid):
    return User(userid)

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return """
        <p>Logged out</p>
        <p><a href="/">Return to /</a></p>
        """
#@app.route('/')
#def hello_world():
    #return 'Hello World!'

@app.route('/smoker',methods=['GET'])
def list_smokers():
	db = get_db()
	cursor = db.cursor()
	cursor.execute("select * from smoker")
	dbsmokers = cursor.fetchall()
	cursor.close()

	smokers = []
	for smoker in dbsmokers:
		unit = dict()
		unit['id'] = smoker[0]
		unit['name'] = smoker[1]
		smokers.append(unit)

	return jsonify(smokers=smokers)

@app.route('/smoker/<int:smoker_id>/io', methods=['GET'])
def list_io(smoker_id):
	db = get_db()
	cursor = db.cursor()
	cursor.execute("""select id,name,unit,unit_abbrev from smoker_io where smoker_id = %s;""",(smoker_id,))
	db_io = cursor.fetchall()
	cursor.close()

	io = []
	for io_dev in db_io:
		io.append(dict(id=io_dev[0],name=io_dev[1],unit=io_dev[2],unit_abbrev=io_dev[3]))

	return jsonify(smoker_io=io)

@app.route('/values/<int:smoker_id>/<varname>',methods=['GET'])
@login_required
def get_io_values(smoker_id,varname):
	db = get_db()
	cursor = db.cursor()

	starttime = request.args.get('start','')
	interval = request.args.get('interval',15)
	time_interval = int(interval)
	#try:
		#start = datetime.strptime(starttime,'%Y%m%d-%H:%M:%S.%f')
	#except:
		#start = None

	if starttime == '':
		cursor.execute("""select time,value,unit_abbrev from values join smoker_io on smoker_io.id = values.smoker_io_id where varname = %s and smoker_io.smoker_id = %s order by time desc limit 1;""",(varname,smoker_id))
		val = cursor.fetchone()
		cursor.close()
		return jsonify(time=val[0],value=val[1],units=val[2])
	else:
		start = datetime.strptime(starttime,'%Y%m%d-%H:%M:%S.%f')
		cursor.execute("""select time,value
					from values join smoker_io on smoker_io.id = values.smoker_io_id 
					where varname = %s and smoker_io.smoker_id = %s and time > %s order by time;""",
					(varname,smoker_id,start))
		val = cursor.fetchall()
		cursor.close()
		wi = weighted_intervals(val,time_interval)
		wi.append(current_user.name)
		return jsonify(result=wi)


@app.route('/smoker/<int:smoker_id>/power/batterycharge',methods=['GET'])
def get_battery_charge(smoker_id):
	db = get_db()
	cursor = db.cursor()
	cursor.execute("""select time,value from values join smoker_io on smoker_io.id = values.smoker_io_id where varname = %s and smoker_io.smoker_id = %s order by time desc limit 1;""",("batvoltage",smoker_id))
	val = cursor.fetchone()
	cursor.close()
	voltage = val[1]

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

	return jsonify(time=val[0],value=charge,units='%')

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0",port=8000)
