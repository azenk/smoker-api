from sqlalchemy import Table,Column,Integer,String,Enum,Float,ForeignKey,DateTime,desc
from sqlalchemy.orm import mapper,relationship,backref
from database import metadata,db_session

class Smoker(object):
	query = db_session.query_property()

	def __init__(self,smoker_id=None):
		self.smoker_id = smoker_id
		pass

	def __repr__(self):
		return "<Smoker %r>" % (self.name)

smoker_table = Table('smoker',metadata,
	Column('id',Integer, primary_key=True),
	Column('name',String(255))
)

mapper(Smoker,smoker_table)
	

class SmokerIO(object):
	query = db_session.query_property()
	def __init__(self):
		pass

	def __repr__(self):
		return '<SmokerIO %r>' % (self.varname)

	def latestvalue(self):
		iovq = IOValue.query.join(IOValue.smoker_io).filter(SmokerIO.smoker_id == self.smoker_id).filter(SmokerIO.varname == self.varname)
		value = iovq.order_by(desc(IOValue.time)).first()
		return value

smokerio_table = Table('smoker_io',metadata,
	Column('id',Integer,primary_key=True),
	Column('smoker_id',Integer,ForeignKey('smoker.id')),
	Column('name',String(255)),
	Column('unit',String(255)),
	Column('unit_abbrev',String(5)),
	Column('varname',String(30)),
	Column('vartype',Enum('input','output','parameter'))
)

mapper(SmokerIO,smokerio_table,properties={'smoker':relationship(Smoker,backref=backref('io'))})

class IOValue(object):
	query = db_session.query_property()
	def __init__(self,smoker_io_id=None,time=None,value=None):
		self.smoker_io_id = smoker_io_id
		self.value = value
		self.time = time

	def __repr__(self):
		return '<IOValue %r>' % (self.value)

values_table = Table('values',metadata,
	Column('smoker_io_id',Integer,ForeignKey('smoker_io.id'),primary_key=True),
	Column('time',DateTime,primary_key=True),
	Column('value',Float)
)

mapper(IOValue,values_table,
				properties={
					'smoker_io':relationship(SmokerIO,backref=backref('values'))})

class Cook(object):
	query = db_session.query_property()

	def __init__(self,id=None):
		self.id = id
	
	def __repr__(self):
		return '<Cook %d>' % self.id


cook_table = Table('cook',metadata,
	Column('id',Integer,primary_key=True),
	Column('smoker_id',Integer,ForeignKey('smoker.id')),
	Column('start',DateTime),
	Column('stop',DateTime),
	Column('name',String(255)),
	Column('description',String)
)
	
mapper(Cook,cook_table,properties={'smoker':relationship(Smoker,backref=backref('cooks'))})


class Note(object):
	query = db_session.query_property()

	def __init__(self,id=None,cook_id=None):
		self.id = id
		self.cook_id = cook_id
	
	def __repr__(self):
		return '<Note %d>' % self.id


note_table = Table('note',metadata,
	Column('id',Integer,primary_key=True),
	Column('cook_id',Integer,ForeignKey('cook.id')),
	Column('time',DateTime),
	Column('note',String)
)
	
mapper(Note,note_table,properties={'cook':relationship(Cook,backref=backref('notes'))})

class Weather(object):
	query = db_session.query_property()

	def __init__(self,id=None, **kwargs):
		if "station_id" in kwargs:
			self.station_id = kwargs["station_id"]
		if "observation_time" in kwargs:
			self.observation_time = kwargs["observation_time"]
		if "temperature_c" in kwargs:
			self.temperature_c = kwargs["temperature_c"]
		if "wind_degrees" in kwargs:
			self.wind_degrees = kwargs["wind_degrees"]
		if "wind_kph" in kwargs:
			self.wind_kph = kwargs["wind_kph"]
		if "pressure_mb" in kwargs:
			self.pressure_mb = kwargs["pressure_mb"]
		if "dewpoint_c" in kwargs:
			self.dewpoint_c = kwargs["dewpoint_c"]
		if "precip_1hr_metric" in kwargs:
			self.precip_1hr_metric = kwargs["precip_1hr_metric"]

	def __repr__(self):
		return '<Weather %s>' % self.station_id

weather_table = Table('weather',metadata,
	Column('id',Integer,primary_key=True),
	Column('station_id',String),
	Column('observation_time',DateTime),
	Column('temperature_c',Float),
	Column('wind_degrees',Float),
	Column('wind_kph',Float),
	Column('pressure_mb',Float),
	Column('dewpoint_c',Float),
	Column('precip_1hr_metric',Float)
)

mapper(Weather,weather_table)
