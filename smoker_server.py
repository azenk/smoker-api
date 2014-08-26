import SocketServer
import threading
import psycopg2
from datetime import datetime,timedelta
from smokerlib import *

valuecache = dict()

class MyTCPHandler(SocketServer.StreamRequestHandler):
    timeout = 1

    def insertvalue(self,sensorname,value):
			io = SmokerIO.query.filter(SmokerIO.smoker_id == 1).filter(SmokerIO.varname == sensorname).first()
			try:
				previous = io.latestvalue()
			except:
				previous = None
		
			if previous == None or previous.value != value or (datetime.now().replace(tzinfo=previous.time.tzinfo) - previous.time) > timedelta(seconds=14):
				if sensorname in valuecache:
					database.db_session.add(valuecache[sensorname])
					del valuecache[sensorname]
				v = IOValue(smoker_io_id = io.id,value=value)
				database.db_session.add(v)
			else:
				time = datetime.now()
				v = IOValue(smoker_io_id = io.id,time=time,value=value)
				valuecache[sensorname] = v


    def handle(self):
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
				print("Connection opened, sending saved parameters")
				params = SmokerIO.query.filter(SmokerIO.smoker_id == 1).filter(SmokerIO.vartype == 'parameter').all()
				for param in params:
					self.wfile.write("%s:%f\n" % (param.varname,param.latestvalue().value))
					print("%s:%f" % (param.varname,param.latestvalue().value))
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

				database.db_session.commit()
				if error_count >= 3:
					print("Closing Connection due to errors")

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

