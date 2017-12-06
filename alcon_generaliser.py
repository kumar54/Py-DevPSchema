from gi.repository import GObject
from Schema import Schema
from WorldState import WorldState
from Pair import Pair
from Trio import Trio
from Action import Action
import random
import numpy as np
class AlConGeneraliser(GObject.Object):

	def __init__(self, memory):
		self.mem = memory


	def assimilate(self, schema, schemas, updated = False):
		"""Generalise schema by finding similar schemas from list 'schemas'"""
		#if len(schema.associated_observations.state)>0:
		#	print "Schema with associate observations can't generalised"
		#	return 0
		similar = []; similar_generalised = []; similar_ids = []
		if not updated:
			similar.append(schema)
		action = Action()
		target_used = True

		if(len(schema.preconditions.state) == 0 or schema.generalised):
			print "Schmema is either already generalised or with no precondition"
			return 1
		similar_action_states = WorldState()
		state_size = 100
		relate= self.find_relation_pres_post(schema)
		#print "Relations in Schema to be generalised:", relate
		for schema2 in schemas:
			if (schema.id == schema2.id) or len(schema2.preconditions.state) == 0:# Find un-generalised schema
				continue

			if schema2.generalised:
				schema2.set_vars_from_state(schema.preconditions)
				if (self.state_types_match(schema.preconditions.union(schema.associated_preconditions), schema2.preconditions.union(schema2.associated_preconditions)) and self.state_types_match(schema.postconditions.union(schema.associated_observations), schema2.postconditions.union(schema2.associated_observations))) and (schema2.action.name) == (schema.action.name):
						similar_generalised.append(schema2)
				else:
					continue
			#print "states type match %i:"%schema2.id, self.state_types_match(schema.preconditions.union(schema.associated_preconditions), schema2.preconditions.union(schema2.associated_preconditions)), self.state_types_match(schema.postconditions.union(schema.associated_observations), schema2.postconditions.union(schema2.associated_observations))
			if self.state_types_match(schema.preconditions.union(schema.associated_preconditions), schema2.preconditions.union(schema2.associated_preconditions)) and self.state_types_match(schema.postconditions.union(schema.associated_observations), schema2.postconditions.union(schema2.associated_observations)):
				if (schema2.action.name) == (schema.action.name):
					#print "Relations:", relate, self.find_relation_pres_post(schema2)
					if self.relation_match(relate, self.find_relation_pres_post(schema2)):
						#print "Schema is similar: ", schema2.id
						similar.append(schema2); similar_ids.append(schema2.id)
		total = len(similar)
		if (total < 2):
			print "Similar schemas are %i , less than threshold (3): "%len(similar)
			return 2
		else:
			print "Similar schemas found for generalisation: ", [s.id for s in similar]
		state_props = {}
		self.variables = {}; self.pvars = []; idd = None

		props =  schema.action.get_concrete_properties()
		props.update(schema.action.coords.concrete_coords)

		for p in props.keys():
			if self.variables.has_key(p) or not(self.diff_props_in_similar(p, props[p], similar, schema.id) or p in schema.action.coords.concrete_coords.keys()):
				continue
			#print "Finding variable:", p, props[p]
			pvar = "$%c"%random.randint(97,122)
			while(pvar in self.pvars):
				pvar = "$%c"%random.randint(97,122)
			self.variables[p] = Pair(props[p], pvar); self.pvars +=[pvar]

		for o in schema.preconditions.state:
			for p in o.props.keys():
				if self.variables.has_key(p) or not self.diff_props_in_similar(p, o.props[p], similar, schema.id):
					continue
				#print "Finding variable1:", p
				pvar = "$%c"%random.randint(97,122)
				while(pvar in self.pvars):
					pvar = "$%c"%random.randint(97,122)
				self.variables[p] = Pair(o.props[p], pvar); self.pvars +=[pvar]
			for p in o.coords.concrete_coords.keys():
				if self.variables.has_key(p) or not self.diff_props_in_similar(p, o.coords.concrete_coords[p], similar, schema.id):
					continue
				#print "Finding variable2:", p, o.coords.concrete_coords[p]
				pvar = "$%c"%random.randint(97,122)
				while(pvar in self.pvars):
					pvar = "$%c"%random.randint(97,122)
				self.variables[p] = Pair(o.coords.concrete_coords[p], pvar); self.pvars +=[pvar]

		for o in schema.postconditions.state:
			for p in o.props.keys():
				if self.variables.has_key(p) or not self.diff_props_in_similar(p, o.props[p], similar, schema.id):
					continue
				#print "Finding variable3:", p, props[p]
				pvar = "$%c"%random.randint(97,122)
				while(pvar in self.pvars):
					pvar = "$%c"%random.randint(97,122)
				self.variables[p] = Pair(o.props[p], pvar); self.pvars +=[pvar]
			for p in o.coords.concrete_coords.keys():
				if self.variables.has_key(p) or not self.diff_props_in_similar(p, o.coords.concrete_coords[p], similar, schema.id):
					continue
					#print "Finding variable4:", p, o.coords.concrete_coords[p]
				pvar = "$%c"%random.randint(97,122)
				while(pvar in self.pvars):
					pvar = "$%c"%random.randint(97,122)
				self.variables[p] = Pair(o.coords.concrete_coords[p], pvar); self.pvars +=[pvar]

		trial_schema = schema.copy()
		#ignored = self.ignore_obsevations(trial_schema, self.variables)
		trial_schema.generalised = True

		#for p in self.variables.keys(): print "Key:", p, "  value:", self.variables[p].first, "  to be:", self.variables[p].second

		if(len(self.variables) == 0):
			print "No variables found to generalise"
			return 9
		#print "TEST:::::::::::::::::::::::;", trial_schema.postconditions.to_string()
		self.generalise_state(trial_schema.preconditions, self.variables)
		self.generalise_state(trial_schema.associated_preconditions, self.variables)
		self.generalise_action(trial_schema.action, self.variables)
		self.generalise_state(trial_schema.postconditions, self.variables)
		self.generalise_state(trial_schema.associated_observations, self.variables)
		self.generalise_state(trial_schema.disappeared_observations, self.variables)
		print "Sending trial to test for another exisiting generalised schema\n",trial_schema.to_string()
		if(self.generalisation_exists(trial_schema, schemas)):
			print "Generalised schema already exists in another form."
			return 5
		else:
			print "@alcon No similar generalised schema found\n"
		total = float(len(similar)); satisfaction = 0.0; similar_ids = []
		for s2 in similar:
			trial_schema.set_vars_from_state(s2.preconditions)
			sim = trial_schema.get_similarity(s2)
			print "\n@alcon Similrity btw Trial and Schema %i is: %f"%(s2.id, sim)
			if sim > 0.70:
				satisfaction +=1; similar_ids.append(s2.id)
			else:
				print "@alcon No Satisfaction %i:"%s2.id, trial_schema.preconditions.get_similarity(s2.preconditions), trial_schema.postconditions.get_similarity(s2.postconditions)

		if (satisfaction/total) >= 0.5:
			print "@alcongen Generalised schema created:\n"#, trial_schema.to_xml()
			self.mem.emit("connect_action", trial_schema.action)
			#trial_schema.parent_schemas = list(similar_ids)
			trial_schema.generalised = True
			self.mem.add_schema(trial_schema)
			for s in self.mem.schemas:
				if s.id == trial_schema.id:
					continue
				f_post = trial_schema.associated_observations.union(trial_schema.postconditions.union(trial_schema.disappeared_observations)).copy()
				self.mem.remove_ignored_preconditions(f_post)
				f_pre = trial_schema.associated_preconditions.union(trial_schema.postconditions).copy()
				self.mem.remove_ignored_preconditions(f_pre)

				s_post = s.associated_observations.union(s.postconditions.union(s.disappeared_observations)).copy()
				self.mem.remove_ignored_preconditions(s_post)
				s_pre = s.associated_preconditions.union(s.preconditions).copy()
				self.mem.remove_ignored_preconditions(s_pre)

				if s_post.equivalents(f_pre): #and len(s_post.state) == len(f_pre.state):
					if not trial_schema.id in s.child_schemas:
						s.child_schemas.append(trial_schema.id)
					if not s.id in trial_schema.parent_schemas:
						trial_schema.parent_schemas.append(s.id)
				if f_post.equivalents(s_pre):# and len(f_post.state) == len(s_pre.state):
					if not s.id in trial_schema.child_schemas:
						trial_schema.child_schemas.append(s.id)
					if not trial_schema.id in s.parent_schemas:
						s.parent_schemas.append(trial_schema.id)
			return 8.5
		else:
			print "Trial schema failed with satisfaction:",satisfaction, total, "\n"
		return 6



	def generalise_action(self, act, variables):
		"""Generalise action of the schema if action contains properties"""
		#print "@generalise-action Variables::::::::::::: ", act.props, act.props_var
		ps = act.props.copy()
		ps.update(act.coords.concrete_coords)
		for p in ps.keys():
			#print "@generalise-action Props: ", p, act.props[p], variables[p].first, variables[p].second, variables[p].first == act.props[p]
			if not variables.has_key(p):
				continue
			if variables[p].first == ps[p]:
				act.set_property_var(p, variables[p].second)
			else: #Value not same? find function
				fx = None; answer = None
				fx = self.find_relation(ps[p], variables[p].first, p)
				if (fx != None):
					if ("-" in fx):
						answer = "%s+%c"%(variables[p].second,fx[1])
					else:
						answer = "%s-%s"%(variables[p].second,fx)
					act.set_property_var(p, answer)
				else:
					answer = variables[p].second
					act.set_property_var(p, answer)
		print "@alcon Generalised Action: ", act.to_string()


	def generalise_state(self, states, variables):
		"""Generalise WS (Pre/Post) based or list (of Trios) created from Preconditions"""
		print "@alcon State to be generalised:\n", states.to_string()
		for o in states.state:
			ps = o.get_properties()
			ps.update(o.coords.concrete_coords)
			for p in ps.keys():
				if not variables.has_key(p):
					continue
				#print "Variables::::::::::::: ", p, variables[p].first, ps[p], variables[p].first == ps[p]
				if type(variables[p].first) == type(ps[p])==type(float()) and abs(variables[p].first -ps[p]) <10.0:
					o.set_property_var(p, variables[p].second)
				else: #Value not same? find function
					print "Value didn't match; Moving to functional generalisation:",p, ps[p], variables[p].first
					fx = None; answer = None
					fx = self.find_relation(ps[p], variables[p].first, p)
					print "Function found:", ps[p], variables[p].first, fx
					if (fx != None):
						if ("-" in fx):
							answer = "%s+%c"%(variables[p].second,fx[1])
						else:
							answer = "%s-%s"%(variables[p].second,fx)
						o.set_property_var(p, answer)
					else:
						answer = variables[p].second
						o.set_property_var(p, answer)
		print "@alcon Generalised States:\n", states.to_string()
		return


	def generalise_state2(self, states, variables):
		"""Generalise WS (Pre/Post) based or list (of Trios) created from Preconditions"""
		print "@alcon State to be generalised:\n", states.to_string()
		for o in states.state:
			ps = o.get_properties()
			ps.update(o.coords.concrete_coords)
			for p in ps.keys():
				if not variables.has_key(p):
					continue
				#print "Variables::::::::::::: ", p, variables[p].first, ps[p], variables[p].first == ps[p]
				if variables[p].first == ps[p]:
					o.set_property_var(p, variables[p].second)
				else: #Value not same? find function
					print "Value didn't match; Moving to functional generalisation:",p, ps[p], variables[p].first
					fx = None; answer = None
					try:
						m, b = self.find_relation2(ps[p], variables[p].first, p)
						answer = "$%.3f*%s+%.3f"%(m, variables[p].second[1],b)
						o.set_property_var(p, answer)
					except:
						answer = variables[p].second
						o.set_property_var(p, answer)
		print "@alcon Generalised States:\n", states.to_string()
		return


	def generalisation_exists(self, test_schema, schemas):
		"""Return True if test_schema aleardy exists in the memory"""
		exists = False
		for s2 in schemas:
			if(not s2.generalised):
				continue
			if (not self.state_types_match(test_schema.preconditions.union(test_schema.associated_preconditions), s2.preconditions.union(s2.associated_preconditions))) or not (self.state_types_match(test_schema.postconditions.union(test_schema.associated_observations), s2.postconditions.union(s2.associated_observations))) or not(self.state_types_match(test_schema.disappeared_observations, s2.disappeared_observations)):
				print "Test to match generalised states type match failed:",s2.id
				exists = False; continue
			else:
				exists = True
			if(not self.matching_generalised_states(test_schema.postconditions.union(test_schema.associated_observations), s2.postconditions.union(s2.associated_observations))):
				print "Test to match generalised state properties match failed:",s2.id
				exists = False; continue
			else:
				exists = True
			if (test_schema.action.name == s2.action.name):
				props = test_schema.action.get_properties()
				props.update(test_schema.action.coords.get_coords())
				props2 = s2.action.get_properties()
				props2.update(s2.action.coords.get_coords())
				if len(props)>0:
					for p in props.keys():
						if not props2.has_key(p):
							exists = False; break
						elif type(props[p]) != type(props2[p]):
							if not "$" in str(props2[p]):
								print "Property not generalised", p, props[p], props2[p]
								exists = False; break
						elif (("$" in str(props[p]) and "$" in str(props2[p])) and (len(str(props[p])) == len(str(props2[p])))):
							exists = True; continue
						elif props[p] != props2[p]:
							print "Property not equal", p, props[p], props2[p]
							exists = False; break
				elif len(props) != len(props2):
					print "Generalised properties don't match"
					exists = False; continue

				if exists:
					print "Test schema is matches another generalised schema:", s2.id
					return exists
			else:
				exists = False; continue
		print "Test schema is matches another generalised schema:", s2.id
		return exists


	def state_types_match(self, ws, ws2):
		""" Return True if type and size of sensors matches between two WSs"""
		if (len(ws.state) != len(ws2.state)):
			return False
		#ws2c = ws2.copy(); wsc = ws.copy()
		for o in ws.state:
			match1 = False;
			for o2 in ws2.state:
				if (o.name == o2.name):
					match1 = True
			if (not match1):
				return False
		return True


	def matching_generalised_states(self, ws, ws2):
		"""Returns if to states have matching generalised properties"""
		match = True
		for o in ws.state:
			match = True
			props = o.get_properties()
			for o2 in ws2.state:
				if o.name != o2.name:
					continue
				props2 = o2.get_properties()
				for p in props.keys():
					if not props2.has_key(p):
						match = False; continue
					if type(props2[p]) == type(str()):
						if type(str()) == type(props[p]):
							if "$" in str(props[p]) and "$" in str(props2[p]) and len(str(props[p])) == len(str(props2[p])):
								#print "Match found1:", p, props[p], props2[p]
								match = True; continue
							else:
								#print "Match found1:", p, props[p], props2[p]
								match = False; continue
						else:
							#print "Match found2:", p, props[p], props2[p]
							match = False; continue

					"""elif type(props[p]) != type(props2[p]):
						if not "$" in str(props2[p]):
							match = False;
					elif type(props[p]) == type(props2[p]):
						if type(str())== type(props[p]):
							if not("$" in str(props[p]) and "$" in str(props2[p]) and len(str(props[p])) == len(str(props2[p]))):
								match = False;
						elif type(props[p]) == type(props2[p])==type(float()) and abs(props[p] - props2[p])> 10:
								match = False;"""
			if not match:
				print "Matching genralised states failed:", p,props[p], props2[p]
				return match
		return match




	def find_relation(self, p1, p2, prop):
		"""Find functional relation between two properties"""
		#print "Finding relation:", type(p1), p1, type(p2), p2, type(p1) == type(p2) == type(1.0)
		if type(p1) == type(p2) == type(float()) and p2 != None:
			m = float(p2) - float(p1)
			#print "Relation:", m
			if abs(m):
				n = str(m)
				return n
			else:
				return None
		else:
			return None


	def find_relation2(self, p1, p2, prop):
		"""Find functional relation between two properties"""
		#print "Finding relation:", type(p1), p1, type(p2), p2, type(p1) == type(p2) == type(1.0)
		if (type(p1) == type(p2)== type(float())) and p2 != None:
			x = np.array([p1])
			y = np.array([p2])
			m, b = np.polyfit(x, y, 1)
			#print "Relation:", m, b
			return round(m,3), round(b, 3)
		return None

	def find_relation_pres_post(self, s):
		"""Finds relation between precondition and postconditions of given schema
		Returns dictionary containg observation names along with property name and relation"""
		observe_pair = {}; added = False
		for o1 in s.preconditions.state:
			added_all = False
			for o2 in s.postconditions.state:
				if o1.name != o2.name or o1.is_generalised() or o2.is_generalised():
					continue
				ps1 = o1.get_concrete_properties(); ps2 = o2.get_concrete_properties()
				#print ps1, ps2
				for p1 in ps1.keys():
					added = False
					relate = self.find_relation(ps1[p1], ps2[p1], p1)
					if observe_pair.has_key(str(o1.name)):
						found = False
						for P in observe_pair[str(o1.name)]:
							if P == p1 and observe_pair[str(o1.name)][P] == relate:
								found = True
						if not found:
							observe_pair[str(o1.name)][p1] = relate; added = True
					else:
						observe_pair[str(o1.name)]= {}
						observe_pair[str(o1.name)][p1] = relate; added = True
				if added:
					break
		return observe_pair




	def relation_match(self, r1, r2):
		"""Checks if two dictionaries of relations matches
		One dictionary is from schema to be generalised
		Other is from similar schema
		Two schemas are considered similar if states_type-match and relation b/w Pres and Post is same"""
		for T1 in r1.keys():
			match = False
			for T2 in r2.keys():
				if T1 != T2:
					continue
				for t1 in r1[T1]:
					if r1[T1][t1] == r2[T1][t1]:
						match = True; break
			if not match:
				#print "Relations do not match"
				return False
		#print "Relation match found"
		return True

	def diff_props_in_similar(self, property, val, similar, origin_id):
		"""To check if property has different values in similar schemas"""
		for s in similar:
			if origin_id != None and (s.id == origin_id):
				continue
			for o in s.preconditions.state:
				properties = o.get_properties()
				#if properties.has_key(property):
				#	print  property, val, properties[property],type(properties[property])== type(val)==type(float()), (properties[property]-val)>10
				if properties.has_key(property):
					if type(properties[property])== type(val)==type(float()):
						if abs(properties[property]-val)>10.0:
							#print "Property in different state: ", property, val, properties[property], type(properties[property])
							return True
					elif (properties[property] != val):
						#print"Property in different state1: ", property, val, properties[property]
						return True
				properties = o.coords.get_coords()
				if (properties.has_key(property) and abs(properties[property] -val)>1.5):
					#print "Property in different state2: ", property, val, properties[property]
					return True
			"""for o in s.postconditions.state:
				properties = o.get_properties()
				if (properties.has_key(property) and properties[property] != val):
					#print "Property in different state: ", property, val, properties[property]
					return True
				properties = o.coords.get_coords()
				if (properties.has_key(property) and properties[property] != val):
					#print "Property in different state: ", property, val, properties[property]
					return True
			properties = s.action.get_properties()
			if (properties.has_key(property) and properties[property] != val):
				#print "Property in different state: ", property, val, properties[property]
				return True"""
			properties = s.action.coords.get_coords()
			if (properties.has_key(property) and abs(properties[property] -val)>1.5):
				#print "Property in different state3: ", property, val, properties[property]
				return True
		return False


	def ignore_obsevations(self, trial_schema, variables):
		ignored = WorldState()
		for o in trial_schema.preconditions.state:
			ps = o.get_properties()
			for p in ps.keys():
				#print "Variable Test1 :",variables.has_key(p), p
				if variables.has_key(p) and type(variables[p].first)==type(float()):
					if variables[p].first == ps[p]:
						continue
					else:
						ignored.add_observation(o); break


		#print "\nIgnored",ignored.to_string()
		for o in ignored.state:
			trial_schema.postconditions.remove_observation(o)
			trial_schema.preconditions.remove_observation(o)
		return ignored