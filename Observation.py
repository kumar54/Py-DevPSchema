import xml, inspect
from abc import abstractmethod,ABCMeta
from gi.repository import GObject
from Coordinates import Coordinates

class Observation(GObject.Object):

	def __init__(self):
		GObject.Object.__init__(self)
		self.activations = 0.0
		self.successes = 0.0
		self.transitory = False
		self.memory_limit = 10000.0
		self.props = {}
		self.props_var = {}
		#self.self_flag  = False
		self.id = -1
		self.coords = Coordinates()
		self.excitation = 0.0


	def get_properties(self):
		"""Get Dictionary containing propserties
		Variable value is returned if exists else concrete is returned"""
		ps = {};  #print "Props: ", self.props, self.props_var
		for p in self.props.keys():
			#print "In props_var: ", p
			if self.props_var.has_key(p) and self.props_var[p] != None:
				ps[p] = self.props_var[p]
			else:
				ps[p] = self.props[p]
		return ps


	def get_var_properties(self):
		"""Returns variable properties of the observation"""
		ps = {}
		for p in self.props_var.keys():
			ps[p] = self.props_var[p]
		return ps

	def get_concrete_properties(self):
		"""Returns concrete properties, having concrete value not generalised"""
		props = {}
		for p in self.props.keys():
			#print "Getting concrete props:", p, self.props[p]
			if self.props[p] != None:
				props[p] = self.props[p]
			else:
				props[p] = self.props_var[p]
		return props


	#Is self in others' lsit
	def __eq__(self, other):
		return self.equals(other)


	def equals(self, o2, ignore = False):
		"""Returns True if two observations are equal"""
		props = self.get_concrete_properties(); props2 = o2.get_concrete_properties()
		#print "Testing if observations equal:",props, props2
		if self.name != o2.name or self.self_flag != o2.self_flag:
			return False
		#print "Props Match:", self.get_concrete_properties(), o2.get_concrete_properties(), self.get_concrete_properties() == o2.get_concrete_properties(), self.get_similarity(o2)

		for p2 in props2.keys():
			if not(props.has_key(p2)):
				return False
			#print "Observation prop type: ", type(props[p2]),type(props2[p2])
			if (type(props[p2]) == type(props2[p2]) == type(float())):
				if self.name == "touching:":
					print "#######touching props:",props[p2], props2[p2]

				if abs(abs(props[p2]) - abs(props2[p2])) > 0:
					return False
			elif (props[p2] != props2[p2]):
				return False

		T = self.coords.equals(o2.coords)
		#print "\nMatching coords", self.coords.get_coords(), o2.coords.get_coords(), T
		if not T:
			#print "Coordinates don't match"
			return False
		return True

	def similar(self, o2, coords = True):
		"""Returns True if two observations are equal"""
		#print "Testing if observations equal:",props, props2
		if self.name != o2.name or self.self_flag != o2.self_flag:
			return False
		props = self.get_concrete_properties(); props2 = o2.get_concrete_properties()
		#print "Concrete_props_similar:", props, props2
		for p2 in props2.keys():
			if not(props.has_key(p2)):
				#print "Property not found:", p2
				return False
			if(props[p2] != props2[p2]):
				#print "Property value not found:",p2,props[p2],type(props[p2]),  props2[p2],type(props2[p2]), (props[p2] != props2[p2])
				return False
			if coords and  props[p2] != props2[p2]:
				return False
		#print "Observation equals: ", props, props2
		return True

	def equivalents(self, o2, ignore = False):
		"""Returns True if two observations are equal"""
		#print "Testing if observations equal:",props, props2
		if self.name != o2.name or self.self_flag != o2.self_flag:
			return False
		props = self.get_properties(); props2 = o2.get_properties()
		for p2 in props2.keys():
			if not(props.has_key(p2)):
				return False
		#print "Observation equals: ", props, props2
		return True

	def copy(self):
		"""Create copy of the observation"""
		o2 = Observation()
		o2.memory_limit = 100.0
		o2.transitory = self.transitory
		o2.props = dict(self.props)
		o2.props_var = dict(self.props_var)
		o2.name = "%s"%self.name
		o2.self_flag = bool(self.self_flag)
		o2.activations = float(self.activations)
		o2.successes = float(self.successes)
		o2.id = int(self.id)
		o2.coords = self.coords.copy()
		o2.excitation = float(self.excitation)
		#print "Observation: Successes: ", self.successes
		#o2.set_property("sensor_id", self.sensor_id)
		#print "O.copy():", o2.props, self.props, inspect.stack()[1][3]
		return o2


	def set_property_var(self, name, val):
		"""Set value for the variable properties"""
		try:
			value = float(val)
		except:
			try:
				value = int(val)
			except:
				value = str(val)
		#print "Setting value: ", name, type(value), value
		if name == "x" or name == "y":
			self.coords.set_variable_coords(name, value)
			return
		self.props_var[str(name)] = value
		self.props[str(name)] = None
		#print "Value set: ", name, self.props_var[name]
		return



	def set_concrete_var(self, name, val):
		"""Set value for the concrete property"""
		try:
			value = float(val)
		except:
			try:
				value = int(val)
			except:
				value = str(val)
		if name == "x" or name == "y":
			#print "setting concrete values for id:", self.id, name , value
			self.coords.set_concrete_coords(name, value)
			return
		#print "Seeting value: ", name, type(value), value
		self.props[str(name)] = value
		return


	# Override default similarity calculation because X, Y need to be considered together
	def get_similarity(self, o2, coords_include = False):
		"""Returns similarity between two observations, scalled to 1.0"""
		similarity = 1.0; m_p = 0.0

		o_props = self.get_concrete_properties(); o2_props = o2.get_concrete_properties()
		len_props = len(o2_props.keys())
		len_coords = len(o2.coords.concrete_coords.keys())
		m = 1.0/(1+len_props+len_coords)
		#print "Similarity Check:", self.id,self.props,self.coords.concrete_coords, o2.id, o2.props,o2.coords.concrete_coords
		if self.name != o2.name:
			similarity -= m

		if len_props == 0:
			if len(o_props.keys()) == 0:
				if coords_include:
					if len_coords > 0:
						similarity -= ((1-self.coords.get_similarity(o2.coords))*m*len_coords)
			return similarity

		if coords_include and len_coords > 0:
			m_p = 0.75*similarity/len_props
			sim = self.coords.get_similarity(o2.coords)
			weight = 0.25*(similarity-m)
			similarity = similarity - weight + (sim*weight)
			#print "Obs:", self.props,self.coords.concrete_coords, o2.props,o2.coords.concrete_coords, similarity, m_p
			#print "Similarity till corrds: ",sim, similarity
		elif len_props > 0:
			m_p = 0.9*similarity/len_props
			sim = self.coords.get_similarity(o2.coords)
			weight = 0.1*(similarity -m)
			similarity = similarity - weight + (sim*weight)
		#print "Similarity till Coords here:", similarity
		for p in o2_props.keys():
			if o_props.has_key(p):
				if (type(o2_props[p]) == type(o_props[p]) == type(float())):
					p1 = o_props[p]; p2 = o2_props[p]
					diff = abs(o2_props[p] - o_props[p])
					if bool(diff):
						similarity = similarity + ( (m_p/(2.0+diff)) - (m_p/2.0) )
					continue
				elif (o2_props[p] != o_props[p]):
					similarity -= m_p/2.0
					continue
			else:
				similarity -= m_p
		#similarity /= (1+total_mismtach)
		#print "Similarity obtained:", self.props, self.coords.get_coords(),o2.props, o2.coords.get_coords(), sim, similarity
		return similarity


	def to_string(self):
		"""Returns observation as string to print"""
		builder = ""
		#builder += "%s, "%type(self).__name__
		builder += "<observation ='%s' self_flag = '%r' "%(self.name, self.self_flag)
		prop = self.get_properties()
		for p in prop.keys():
			builder += "%s: %s, "%(p,prop[p])
		coords = self.coords.get_coords()
		for prop in coords.keys():
			builder += "%s ='%s' "%(prop, coords[prop])
		builder += "id= '%i' />\n"%self.id
		return builder


	def to_concrete_string(self):
		"""Returns observation as string to print"""
		builder = ""
		#builder += "%s, "%type(self).__name__
		builder += "<observation ='%s' self_flag = '%r' "%(self.name, self.self_flag)
		prop = self.get_concrete_properties()
		for p in prop.keys():
			builder += "%s: %s, "%(p,prop[p])
		coords = self.coords.get_concrete_coords()
		for prop in coords.keys():
			builder += "%s ='%s' "%(prop, coords[prop])
		builder += "id= '%i' />\n"%self.id
		#print "Concrete_to_string: Props,", prop,"   Coords", coords
		return builder

	def to_xml(self):
		"""Returns observation in XML format"""
		#print "@o.to_xml type:", self.to_string()
		builder = ""
		#builder += "<observation type='%s' "%type(self).__name__
		builder += "<observation type= '%s' name='%s' self_flag= '%r' "%(type(self).__name__, self.name, self.self_flag)
		properties = self.get_properties()
		for prop in properties.keys():
			builder += "%s ='%s' "%(prop, properties[prop])

		coords = self.coords.get_coords()
		for prop in coords.keys():
			builder += "%s ='%s' "%(prop, coords[prop])

		builder += "successes='%f' activations='%f' "%(self.successes, self.activations)
		builder += "id= '%i' />\n"%self.id
		#print "Observation successes: ", self.successes
		return builder


	def get_probability(self):
		"""Returns probaility of observation
		New observation has probability of 1.0"""
		if (self.activations == 0.0):
			return 1.0
		return self.successes/self.activations

	def parse_node(self, node):
		"""Create elememts of the observation from XML format"""
		for child in node.iter():
			for grand in child.attrib.keys():

				try:
					value = float(child.attrib[grand])
				except:
					try:
						value = int(child.attrib[grand])
					except:
						try:
							value = str(child.attrib[grand])
						except:
							value = bool(child.attrib[grand])
				#print "Child, grand:",grand, child.attrib[grand], type(value)
				if (grand == "activations"):
					self.activations = float(value); continue
				elif (grand == "name"):
					self.name = str(value); continue
				elif (grand == "self_flag"):
					#print "@parse_node Self_flag:", value, bool(value), type(value)
					if value == "False":
						self.self_flag = False; continue
					else:
						self.self_flag = True
				elif (grand == "successes"):
					self.successes = float(value); continue
				elif (grand == "id"):
					self.id = int(value); continue
				elif (grand == "parent"):
					self.parentId = int(value); continue
				elif (grand != "type"):
					#print "@parse_node Grand at set: ", grand, value, type(value), type(value) == type(str())#, value[0] == '$'
					if type(value) == type(str()):
						if value[0] == '$':
							self.set_property_var(grand, value); continue
						else:
							self.set_concrete_var(grand, value); continue
					else:
						self.set_concrete_var(grand, value); continue
		#print "Parse_node: ", self.to_string(), self.self_flag

	def occurred(self, success):
		"""Observation successes and activations are recorded"""
		#print "Observation occourences~: ", success, self.to_string(), self.activations, self.successes
		self.activations +=1
		if success:
			self.successes +=1
		#print "Observation occoured~: ", success, self.to_string(), self.activations, self.successes


	def instantiate_var(self, variable, value):
		"""Instantiates the property (variable) with given value """
		props = self.get_properties()
		coords = self.coords.get_coords()
		props.update(coords)
		#print "@intantiate_var Instantiating: ",props, self.coords.get_coords(), variable, value
		for p in props.keys():
			if p != variable:
				continue
			try:
				p_val = float(props[p])
			except:
				try:
					p_val = int(props[p])
				except:
					p_val = str(props[p])
			#print "Values to be instantiated:", p, props[p], p_val, type(p_val) #!= type(str()) and "$" in p_val, (p_val == variable and len(p_val)<3)  (len(p_val)>2 and p == variable)
			if type(p_val) != type(str()) or not("$" in p_val):
				continue
			#print "$ sign found:", "$" in p_val, p_val
			#if not("$" in p_val):
			#	continue
			if (not "-" in p_val) and (not "+" in p_val):
				#print "Setting concrete_values: ", p, value
				self.set_concrete_var(p, value)
			else:#elif(str(p_val) != str(variable) and len(p_val)>2):
				#print "Property with function to be changed:", p, p_val, value
				if type(value) != type(float()):
					return
				try:
					sym = p_val[p_val.index("-")]
				except:
					sym = p_val[p_val.index("+")]
				#sym = p_val[2]
				q = float(value); reply = None
				# s = "0%c"%p_val[3]; w = float(s)
				w = float(p_val[p_val.index(sym)+1:])
				if (sym =='-'):
					reply = q-w
				else:
					reply = q+w
				ss = abs(reply)
				#print "setting concrete Value with function created: ",p, ss
				self.set_concrete_var(p, ss)

	def hash(self):
		"""Create string of the Observation"""
		#print "@o_has:", self.get_concrete_properties()
		builder = ""
		builder +="%s"%str(self.name)
		builder +="%r"%str(self.self_flag)
		properties = self.get_properties()
		for prop in properties.keys():
			builder += "%s%s, "%(prop, properties[prop])
		return builder

	def is_generalised(self):
		"""Returns True if any of the variable is generalised"""
		props = self.get_properties()
		#print "@is_generalised:",  props
		for p in props.keys():
			if("$" in str(props[p])):
				return True
		coords = self.coords.get_coords()
		#print "@is_generalised:",  coords
		for p in coords.keys():
			if("$" in str(coords[p])):
				return True
		return False


GObject.type_register(Observation)
