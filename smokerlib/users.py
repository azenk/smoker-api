class User:
	def __init__(self,userid):
		self.id = userid
		self._name = None

	@property
	def name(self):
		return self._name
	
	@name.setter
	def set_name(self, name):
		_name = name
		
	def is_authenticated(self):
		return True

	def is_active(self):
		return True
	
	def is_anonymous(self):
		return False

	def get_id(self):
		return unicode(self.id)

