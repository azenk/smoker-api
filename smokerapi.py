from flask import Flask
from flask import jsonify
from flask import g
from flask import render_template

from flask.ext.socketio import SocketIO, emit

import psycopg2

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
app.debug = True

def get_db():
	if not hasattr(g, 'database'):
		g.database = psycopg2.connect("dbname=smoker user=apache")
	return g.database

@app.teardown_appcontext
def close_db(error):
	if hasattr(g,'database'):
		g.database.close()

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
def get_io_values(smoker_id,varname):
	db = get_db()
	cursor = db.cursor()
	cursor.execute("""select time,value from values join smoker_io on smoker_io.id = values.smoker_io_id where varname = %s and smoker_io.smoker_id = %s order by time desc limit 1;""",(varname,smoker_id))
	val = cursor.fetchone()
	cursor.close()

	return jsonify(time=val[0],value=val[1])
	
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('my event', namespace='/test')
def test_message(message):
    emit('my response', {'data': message['data']})

@socketio.on('my broadcast event', namespace='/test')
def test_message(message):
    emit('my response', {'data': message['data']}, broadcast=True)

@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0",port=8000)
