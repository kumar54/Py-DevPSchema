from gi.repository import GObject
import time, inspect
class WorldState(GObject.Object):

	def __init__(self, mem= None):
		self.state = []
		self.mem =mem


	def add_observation(self, o):
		"""Add given observation to the World state"""
		found = False; condition = False
		#if o == None:
		#	return
		#print "@@@@@@@Adding Observation",o.to_string(),"\n",len(self.state)
		if len(self.state) <1:
			self.state.append(o)
			return
		for o2 in self.state:
			if (o.equals(o2)):
				#print "Match:", o.props, o2.props
				#o2.occurred(True)
				found = True
				#condition = ( o2.is_generalised() and (type(o2) == type(o)) )
				break
		if not (found):
			self.state.append(o)
		return
		#else:
		#	print "Removing@add_obs:", o.to_string(), found, condition

	def remove_observation(self, o):
		"""Remove given observation from the World state"""
		remove = False; w =WorldState()
		for o2 in self.state:
			if o2.equals(o):
				remove =True; break
		if remove:
			#print o in self.state, self.to_string()
			self.state.remove(o)

	def equals(self, ws2):
		"""Return True if two World states are equal"""
		#print "@WS satisfies:\n", self.to_string(),"Matches with:\n", ws2.to_string()
		return self.satisfies(ws2) and len(ws2.state) == len(self.state)


	def similar(self, ws2, coords = True):
		if (ws2 == None):
			return True
		#if len(ws2.state) != len(self.state):
		#	print "WS are not equal to not similar:", len(self.state), len(ws2.state)
		#	return False
		for o in ws2.state:
			found = False
			for o2 in self.state:
				#print "Matching @@@@:",o.get_concrete_properties(), o.coords.get_coords(), o2.get_concrete_properties(), o2.coords.get_coords()
				if o.similar(o2, coords):
					found = True;break
			if (not found):
				#print "@WS not satisfies:", o.to_string()
				return False
		return True



	def satisfies(self, ws2= None, ignore = False):
		"""Return True if the WS is subset of the given state"""
		if (ws2 == None):
			return True
		for o in ws2.state:
			found = False
			for o2 in self.state:
				#print "Matching @@@@:",o.get_concrete_properties(), o.coords.get_coords(), o2.get_concrete_properties(), o2.coords.get_coords()
				if o.equals(o2):
					found = True;break
			if (not found):
				#print "@WS not satisfies:", o.to_string()
				return False
		return True

	def get_similarity(self, ws2):
		"""Returns similarity between two states
		Similarity is scalled to 1.0"""
		Total_similarity = 0.0
		for o1 in ws2.state:
			similarity = 0.0; last_similarity = 0.0
			for o2 in self.state:
				similarity = o2.get_similarity(o1)
				if similarity > last_similarity:
					last_similarity = similarity
			#print "Observation similarity: ", last_similarity
			Total_similarity += last_similarity
		#print "Ws similarity: ", Total_similarity, Total_similarity/float(len(self.state))
		if len(ws2.state) == 0:
			return Total_similarity
		return Total_similarity/float(len(ws2.state))


	def type_subset(self, ws2):
		"""Retruns if WS is type subset of the given state"""
		found = True
		for o in ws2.state:
			found = False;
			for o2 in self.state:
				if o.name == o2.name:
					found = True
					break
			if (not found):
				return False;
		return found


	def equivalents(self, ws2= None):
		"""Returns true if size and names of obseravtions in two states are same"""
		#print "\nSelf:",self.to_string(),"--------------\n", ws2.to_string()
		for o in ws2.state:
			found = False; same = 0
			for o2 in self.state:
				if o2.equivalents(o):
					found = True; break
			if (not found):
				#print "Equivalent not match:",o.to_string()
				return False
		return True

	def print_to(self):
		"""Retrun WS as string to print"""
		message = "\n"
		for o in self.state:
			message += str(o.to_string())
		print message


	def copy(self):
		"""Create copy of the State"""
		ws = WorldState()
		for o in self.state:
			o2 = o.copy()
			ws.add_observation(o2)
		return ws


	def get_predictions(self):
		"""Get reliable postconditions
		If Postconditions contains multiple sensors of same name then
		Most reliable will be returned"""
		predictions = {}
		for o in self.state:
			if ( predictions.has_key(o.name)):
				if (predictions[o.name].get_probability() < o.get_probability()):
					predictions[o.name] =  o
			else:
				predictions[o.name] = o
		ws = WorldState()
		for sensor_id in predictions.keys():
			ws.add_observation(predictions[sensor_id])
		return ws

	def to_string(self):
		"""Returns WS as string"""
		builder = ""
		for o in self.state:
			builder +=o.to_string()
		return builder


	def to_concrete_string(self):
		"""Returns WS as string"""
		builder = ""
		for o in self.state:
			builder +=o.to_concrete_string()
		#print "\nTo Concrete_sting:::",inspect.stack()[1][3]
		return builder

	def to_xml(self):
		"""Returns WS in XML format"""
		builder = ""
		builder += "<worldstate>\n"
		for o in self.state:
			builder += o.to_xml()
		builder += "</worldstate>\n"
		return builder

	def get_probability(self):
		"""Returns probability of the WS"""
		probability = 1
		predictions = self.get_predictions()
		for o in self.state:
			probability += o.get_probability()
		return probability/len(self.state)

	def complement(self, ws2, sensor_complement=False):
		"""Find complement of the given state from the state (new_state - state)"""
		complement_state = WorldState()
		#print "WS @here\n", ws2.to_string(), "\n", self.to_string()
		for o in ws2.state:
			#print "WS:\n", o.to_string()
			matched = False
			for o2 in self.state:
				#print "Expected:\n", o2.to_string(), matched
				if matched:
					continue
				if(sensor_complement):
					if (o.name == o2.name):
						matched = True
				else:
					if (o.equals(o2)):
						matched = True; break
			if not (matched):
				o2 = o.copy()
				complement_state.add_observation(o2)
		#print "Finding complement between: ", self.to_string(), "\n and \n", ws2.to_string()
		#print "complement state: ", complement_state.to_string()
		return complement_state


	def union(self, ws2):
		"""Returns union of two states"""
		comp = self.complement(ws2, False)
		u = self.copy()
		for o in comp.state:
			u.add_observation(o.copy())
		return u

	def intersection(self, ws2):
		"""Returns intersaction of the two states"""
		n =  WorldState()
		for o in self.state:
			matched = False;
			for o2 in ws2.state:
				if (o2.equals(o)):
					matched = True; break
			if (matched):
				n.add_observation(o)
		return n



	def difference(self, ws2):
		found = False
		diff = WorldState()
		for o in ws2.state:
			found = False
			for o2 in self.state:
				if o2.similar(o):
					found = True; break
			if not found:
				diff.add_observation(o)
		return diff

	def inst_vars(self, concrete_states):
		"""Instantiates variables of the generalised observation form set of concrete values"""
		variables = {}
		for o in concrete_states.state:
			properties = o.get_properties()
			for p in properties.keys():
				if (not variables.has_key(p)):
					variables[p] = properties[p]
		for variable in variables.keys():
			v = variables[variable]
			for o in self.state:
				props = o.get_properties()
				for p in props.keys():
					p_val = props[p]; reply = None
					if(p == variable and len(p_val) < 3):
						o.set_property_var(p, v)
					elif (p == variable and len(p_val) > 2 and len(p) < 3):
						sym = p_val[2]; q = int(v)
						s = "0%c"%p_val[3]; w = int(s)
						if (sym =='-'):
							reply = q-w
						else:
							reply = q+w
					ss = str(abs(reply))
					o.set_property_var(p, ss)
		return variables

GObject.type_register(WorldState)