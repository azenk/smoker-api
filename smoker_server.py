import SocketServer
import threading
import psycopg2
from datetime import datetime,timedelta

valuecache = dict()

class MyTCPHandler(SocketServer.StreamRequestHandler):
    timeout = 1

    def insertvalue(self,sensorname,value):
	cur = self.conn.cursor()
	cur.execute("SELECT id from smoker_io where varname = %s;",(sensorname,))
	id = cur.fetchone()
	cur.execute("SELECT value,time from values where smoker_io_id = %s order by time desc limit 1;",(id,))
	try:
		(previousvalue,previoustime) = cur.fetchone()
	except psycopg2.ProgrammingError, e:
		previousvalue = None
		previoustime = None

	if value != previousvalue or previousvalue == None or (datetime.now().replace(tzinfo=previoustime.tzinfo) - previoustime) > timedelta(seconds=14):
		if sensorname in valuecache:
			cur.execute("INSERT INTO values (smoker_io_id,time,value) VALUES (%s,%s,%s);",
				(id,valuecache[sensorname]["time"],valuecache[sensorname]["value"]))
			del valuecache[sensorname]
		cur.execute("INSERT INTO values (smoker_io_id,value) VALUES (%s,%s);",(id,value))
	else:
		cur.execute("select now();")
		time = cur.fetchone()[0]
		valuecache[sensorname] = {"time": time, "value": value}

	self.conn.commit()
	cur.close()

    def handle(self):
        self.conn = psycopg2.connect("dbname=smoker")
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
	#self.wfile.write("setpoint:1.0\n")
	#self.wfile.write("kp:8.5\n")
	#self.wfile.write("ki:0.01\n")
	#self.wfile.write("kd:-2.5\n")
	self.wfile.write("sendcomplete:1.0\n")
	print("sendcomplete")
	framedone = False
	error_count = 0
	inframe = False
	while not framedone and error_count < 3:
	    try:
        	self.data = self.rfile.readline().strip()
		(sensorname,value) = self.data.split(":",1)
		print("%s:%s" % (sensorname,value))
		if sensorname == "frameend":
			framedone = True
			inframe = False
		elif sensorname == "framestart":
			print "framestart"
			inframe = True
		elif not inframe:
			print "Ignoring %s" % self.data
		else:
			self.insertvalue(sensorname,float(value))
	    except Exception, e:
		error_count += 1
		print(e)

	if error_count >= 3:
		print("Closing Connection due to errors")
	self.conn.close()

        # Likewise, self.wfile is a file-like object used to write back
        # to the client
        #self.wfile.write(self.data.upper())

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 9500

    # Create the server, binding to localhost on port 9999
    SocketServer.TCPServer.allow_reuse_address = True
    server = ThreadedTCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()

