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

import sys

import psycopg2

app = Flask(__name__)
app.secret_key = smokerconfig.sessionsecret
app.config["GOOGLE_LOGIN_CLIENT_ID"] = smokerconfig.google_client_id
app.config["GOOGLE_LOGIN_CLIENT_SECRET"] = smokerconfig.google_client_secret
#app.config["GOOGLE_LOGIN_SCOPES"] = ""
app.config["GOOGLE_LOGIN_REDIRECT_URI"] = "https://smoker.culinaryapparatus.com/devapi/oauth2callback"
app.config["GOOGLE_LOGIN_REDIRECT_SCHEME"] = "https"
app.debug = False
googlelogin = GoogleLogin()
googlelogin.init_app(app)

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler("/websites/applogs/smokerapi.log",maxBytes=10*2**20,backupCount=7)
    file_handler.setLevel(logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)


def get_db():
	if not hasattr(g, 'database'):
		g.database = psycopg2.connect("dbname=smoker user=apache")
	return g.database

@app.teardown_appcontext
def close_db(error):
	database.db_session.remove()
	if hasattr(g,'database'):
		g.database.close()

@app.route('/oauth2callback')
@googlelogin.oauth2callback
def create_or_update_user(token, userinfo, **params):
	app.logger.debug("Entered OAUTH2 Callback")
	app.logger.debug("Received oauth2 callback - userinfo: %s" % repr(userinfo))

	userq = User.query.filter(User.google_id == userinfo["id"])

	if userq.count() < 1:
		# create user
		app.logger.debug("User not found, creating")
		u = User(google_id=userinfo["id"],name=userinfo["name"])
		database.db_session.add(u)
	else:
		# update user if required
		app.logger.debug("User found, updating")
		u = userq.first()	
		if userinfo["name"] != u.name:
			u.name = userinfo["name"]

	app.logger.debug("User %s" % u.name)
	login_user(u)

	database.db_session.commit()
	return redirect('/client/SmokerGraphs.html')

@app.route("/user/info")
def userinfo():
	if current_user.is_anonymous():
		return jsonify(logged_in=False)
	else:
		return jsonify(logged_in=True,name=current_user.name)

@app.route("/login")
@login_required
def login():
	return redirect('/api/profile')

@googlelogin.user_loader
def get_user(userid):
	app.logger.debug("Running user loader: id %s" % userid)
	user = User.query.filter(User.google_id == userid).first()
	app.logger.debug("User %s" % user.name)
	return user

@app.route('/logout')
def logout():
	if current_user.is_authenticated():
		app.logger.debug("Logged out user %s" % current_user.name)
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
	endtime = request.args.get('end','')
	interval = request.args.get('interval',None)

	if starttime == '':
		v = IOValue.query.join(IOValue.smoker_io).filter(SmokerIO.smoker_id == smoker_id).filter(SmokerIO.varname == varname).order_by(desc(IOValue.time)).first()	
		return jsonify(time=v.time,value=v.value,units=v.smoker_io.unit_abbrev)

	basequery = IOValue.query.join(IOValue.smoker_io).filter(SmokerIO.smoker_id == smoker_id).filter(SmokerIO.varname == varname)	

	if starttime != '':
		start = datetime.strptime(starttime,'%Y%m%d-%H:%M:%S.%f')
		basequery = basequery.filter(IOValue.time > start)
	
	if endtime != '':
		end = datetime.strptime(endtime,'%Y%m%d-%H:%M:%S.%f')
		basequery = basequery.filter(IOValue.time <= end)

	v = basequery.order_by(IOValue.time).all()	

	if len(v) == 0:
		return jsonify(result=[])
		
	if interval == None:
		result = map(lambda x: {"time":x.time,"value":x.value,"units":x.smoker_io.unit_abbrev},v)
		return jsonify(result=result)
	else:
		time_interval = int(interval)
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
