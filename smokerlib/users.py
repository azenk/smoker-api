from sqlalchemy import Table,Column,Integer,String,Enum,Float,ForeignKey,DateTime,Boolean
from sqlalchemy.orm import mapper,relationship,backref
from database import metadata,db_session

class User(object):
	query = db_session.query_property()
	def __init__(self,id=None,google_id=None,name=None):
		self.id = id
		self.google_id = google_id
		self.name = name

	def is_authenticated(self):
		return True

	def is_active(self):
		return True
	
	def is_anonymous(self):
		return False

	def get_id(self):
		return unicode(self.id)

user_table = Table('users',metadata,
	Column('id',Integer,primary_key=True),
	Column('google_id',String(255)),
	Column('name',String(255)),
	Column('email',String),
	Column('administrator',Boolean),
	Column('update',Boolean)
)

mapper(User,user_table)
