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

	
