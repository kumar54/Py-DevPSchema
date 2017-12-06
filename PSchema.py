from gi.repository import GObject, Gtk
from Schema import Schema
from WorldState import WorldState
from Action import Action
from Observation import Observation
from alcon_generaliser import AlConGeneraliser
from Pair import Pair
from Chain import Chain
from novelty_calculator import NoveltyCalculator
import xml.etree.ElementTree as ET
import xml, time, csv, inspect, math, datetime
import  statistics as stc

class Memory(GObject.Object):
	__gsignals__ = {
				"connect_action" : (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (Action,)),
				"create_action" : (GObject.SIGNAL_RUN_LAST, Action, (str,)),
				"create_observation" : (GObject.SIGNAL_RUN_LAST, Observation, (str,)),
				"update_state" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ())
	}




	def __init__(self):
		GObject.Object.__init__(self)
		self.schemas = []
		self.ignored_preconditions = []
		self.observations = {}
		self.observations_ids = {}
		self.observation_in_schemas = {}
		self.observation_ids_seen = {}
		self.generalised_associations = {}
		self.chains = []
		self.current_schema = None
		self.current_chain = None
		self.ws = None
		self.predicted_world_state = None
		self.associations = {}
		self.total_generalised_schema_executions = 0
		self.successful_generalised_schema_executions = 0
		self.loading_schema = None
		self.loading_state_type = None
		self.loading_state_type = None
		self.next_id = 0
		self.excited_agents = None
		self.excitation_calculator = NoveltyCalculator(self)
		self.generaliser = AlConGeneraliser(self)
		self.goal = WorldState()
		self.last_executed_id = None
		self.total_executions = 0.0
		self.goal_chain = None
		self.d =  str(datetime.datetime.now().date())
		self.d += str(datetime.datetime.now().time())
		self.e_d = "./Results/Excitation_record_%s.csv"%self.d
		excitations_in_record = open(self.e_d, "w")
		self.t_d ="./Results/Schema_update_record_%s.txt"%self.d
		update_record = open(self.t_d, "w")


	def add_schema(self, s):
		"""Adding new schema to the memory"""
		self.schemas.append(s)
		s.id = self.next_id
		self.next_id +=1

	def add_chain(self, new_chain):
		"""Add chain to the memory, Add if chain doesn't exist already"""
		found = False
		if len(self.chains) > 0 :
			for chainx in self.chains:
				if chainx.sequence == new_chain:
					found = True
					prob = 0.0
					for id in new_chain:
						s = self.get_schema_from_id(id)
						prob += s.get_probability()
					chainx.probability = float(prob)/len(new_chain)
			if (not found):
				C = Chain()
				C.sequence = list(new_chain)
				prob = 0.0
				for id in new_chain:
					s = self.get_schema_from_id(id)
					prob += s.get_probability()
				C.probability = float(prob)/len(new_chain)
				self.chains.append(C)
				return
			else:
				return
		else:
			C = Chain()
			C.sequence = list(new_chain)
			prob = 0.0
			for id in new_chain:
				s = self.get_schema_from_id(id)
				prob += s.get_probability()
			C.probability = float(prob)/len(new_chain)
			self.chains.append(C)
			return


	def create_chain(self, chain):
		#                       print "Testing to add_chain@create_chain", chain.sequence
		if len(self.chains) ==0:
			self.chains.append(chain)
		else:
			found  = False
			for c in self.chains:
				if c.equals(chain):
					found = True; break
			if not found:
				self.chains.append(chain); return
			else:
				print "Chain already exists@create_chain", chain.sequence;return

	def get_chain_from_sequence(self, chain):
		"""Get chain from memory"""
		for C in self.chains:
			if C.sequence == chain.sequence:
				print "Chain found for the sequence:", C.sequence
				return C
		self.add_chain(chain.sequence)

	def get_schema_from_action(self, action):
		"""Get schema from memory containing given action & WS as preconditions"""
		return self.get_schema(self.ws, action, WorldState())

	def get_schema_from_id(self, id):
		"""Returns schema having given ID"""
		return self.schemas[id]


	def remove_ignored_preconditions(self, pres):
		"""Remove ignored observations from given world state; Returns World state"""
		remove = WorldState()
		#print "At reomve"
		"""for o in pres.state:
			if o.sensor_ID in self.ignored_preconditions:#if o.sensor_ID == 0 or o.sensor_ID == 1 or o.sensor_ID == 100 or str(o.sensor_ID)[-2:] == "01":
				remove.add_observation(o)"""
		for o in pres.state:
			#print "At remove: flag ", o.self_flag
			if o.self_flag:
				remove.add_observation(o)
		for o in remove.state:
			#print "Removing"
			pres.remove_observation(o)
		return remove


	def is_ignored(self, sensor_id):
		"""Check if given sensor ID is ignored; Not used in current system (Containg Abstract observations)"""
		if sensor_id in self.ignored_preconditions:
			return True
		else:
			return False

	def ignore_precondition(self, sensor_id):
		"""Add sensor ID into ignored sensors. Not used in abstract observation systems"""
		self.ignored_preconditions.append(sensor_id)



	def remove_transitory_observations(self, ws):
		"""Remove Transitory observations from the given world state"""
		remove = []
		for o in ws.state:
			if (o.transitory):
				remove.append(o)
		for o in remove:
			ws.state.remove(o)

	def get_schema(self, pres, action, posts):
		"""Get schema from the memory with given Pres, action and Post
		If multiple schemas are found then schema with highest probability is returned"""
		if pres != None:
			self.remove_ignored_preconditions(pres)
		found_schema = None; probability = 0.0
		for schema in self.schemas:
			if (schema.satisfies(pres, action, posts)):# and probability < schema.get_probability():
				found_schema = schema
				#probability = schema.get_probability()
				return found_schema
		return found_schema


	def get_or_create_schema(self, preconditions, action, postconditions, use_action = True):
		"""Creat schema from given Pres, action and Posts
		Schema with such states is searched in the memory
		I fnot found then new schema is created; use_action argument defines if schema contains action"""
		self.remove_ignored_preconditions(preconditions)
		if (use_action):
			found_schema = self.get_schema(preconditions, action, postconditions)
		else:
			found_schema = self.get_schema(preconditions, None, postconditions)
		if (found_schema == None):
			found_schema = Schema(self)
			found_schema.preconditions = preconditions
			if (use_action):
				found_schema.action = action
			found_schema.postconditions = postconditions
			found_schema.added_ID = int(self.total_executions)
			self.add_schema(found_schema)
		return found_schema


	def update_schema(self, schema):
		"""Update schema postconditions from given state"""
		found_all = True; schema_changed = False; not_found = WorldState()
		if len(schema.action.coords.concrete_coords.keys()) > 0:
			coords_include = True
		else:
			coords_include = False
		if schema.generalised:
			wsc = self.ws.copy(); self.remove_ignored_preconditions(wsc)
			#schema.set_vars_from_state(wsc)
			s_post = schema.postconditions.union(schema.associated_observations).copy(); self.remove_ignored_preconditions(s_post)
			for o in s_post.state:
				#print "Testing observations:"
				found = False
				if o in wsc.state:
					o.occurred(True)
					found = True; continue
				else:
					o.occurred(False)
					found_all = False
					not_found.add_observation(o.copy())
		else:
			s_post = schema.postconditions.union(schema.associated_observations).copy(); self.remove_ignored_preconditions(s_post)
			for o in s_post.state:
				found = False
				if coords_include:
					if o in self.ws.state:
						o.occurred(True)
						found = True
					else:
						#print "@schem_update Observation not found:", o.to_string()
						not_found.add_observation(o.copy())
						o.occurred(False)
						found_all = False
				else:
					for o2 in self.ws.state:
						if o2.equivalents(o):
							o.occurred(True)
							found = True; break
					if not found:
						not_found.add_observation(o.copy())
						o.occurred(False); found_all = False
		if(len(schema.postconditions.state) == 0):
			schema.successes +=1; schema_changed = True; found_all = False
			for o in self.ws.state:
				if not(o.self_flag):
					continue
				found = False
				for o2 in schema.postconditions.state:
					if (o.equals(o2)):
						found = True; break
				if (not found):
					o.occurred(True)
					schema.postconditions.add_observation(o)
		if found_all:
			schema.successes +=1
			print "Schema succesful@pschema.schema_update:",schema.successes
		return (found_all, schema_changed, not_found)


	def update_world_state(self, new_state):
		"""Update world state of the system from the given state
		System also creates schemas, generalisation in this step
		Schema/chain success is measured here"""
		print "@PSchema_update_W_S: New State\n", new_state.to_string()
		prev_state = None
		if (self.ws != None):
			prev_state = self.ws.copy()
			prev_removed = prev_state.copy(); self.remove_ignored_preconditions(prev_removed)

		self.ws = new_state.copy()
		ws_removed = self.ws.copy(); self.remove_ignored_preconditions(ws_removed)

		if (self.current_schema == None):
			print "No current schema to update:"#, len(self.ws.state)
			for o in self.ws.state:
				if prev_state != None:
					prv_state_ids = [o.id for o in prev_state.state]
					if o.id in prv_state_ids:
						continue
				self.observation_id_occurred(o.id)
				self.observation_ids_seen_at(o)
				print "Observation occured1:", o.id, self.observation_in_schemas[o.id].second if self.observation_in_schemas.has_key(o.id) else "Not in schemas",  self.observation_id_occurrences(o.id)
			return 0
		else:
			print "Current schemas @ update: ",self.current_schema.id
			self.goal = self.current_schema.postconditions.union(self.current_schema.associated_observations).copy()
			for o in self.ws.state:
				self.observation_id_occurred(o.id)
				self.observation_ids_seen_at(o)
				print "Observation occured2:", o.id, self.observation_in_schemas[o.id].second if self.observation_in_schemas.has_key(o.id) else "Not in schemas", self.observation_id_occurrences(o.id)

		#Chain success updating
		if self.current_chain != None:
			print "Current Chain & schema @ update: ", self.current_chain.sequence, self.current_schema.id
			if self.current_schema.id in self.current_chain.sequence: #self.current_chain.chain[-1] != self.current_schema.id and
				if not self.current_schema.generalised:
					if not self.ws.equivalents(self.current_schema.postconditions.union(self.current_schema.associated_observations)):
						print "Chain schema fialed, attempting to achieve through new chain";self.current_chain = None
						"""path = self.find_path3(self.ws.copy(), self.goal, [], None, False)
						if len(path) < 1:
							print "Chain Failed in middle1:"
							self.current_chain = None
						else:
							print "Reattempting to achieve the goal1:"
							if not self.achieve_goal2(self.goal, [self.current_schema.id], False):
								return self.emit("update_state")
							else:
								print "Chain Failed in middle1.1:"
								self.current_chain = None"""
					else:
						if self.current_chain.sequence[-1] == self.current_schema.id:
							print "**Chain exists and executed successfuly**"
							self.current_chain.successes +=1
							self.current_chain = None
						else:
							print "**Chain execution in progress**"
							self.current_schema = None; return 0.1
				else:
					if not self.ws.equivalents(self.current_schema.postconditions.union(self.current_schema.associated_observations)):
						print "Chain Schema not acheived target"; self.current_chain = None
						"""path = self.find_path2(self.ws.copy(), self.goal, [], False)
						if len(path) < 1:
							print "Chain Failed in middle2:"
							self.current_chain = None
						else:
							print "Reattempting to achieve the goal2:"
							self.achieve_goal2(self.goal, [self.current_schema.id], False)
							return self.emit("update_state")"""
					else:
						if self.current_chain.sequence[-1] == self.current_schema.id:
							print "**Chain exists and executed successfuly**"
							self.current_chain.successes +=1
							self.current_chain = None
						else:
							print "**Chain execution in progress**"
							self.current_schema = None; return 0.1

		#Creating schema from Bootstrapping
		successful = self.update_schema(self.current_schema)
		print "Schema update @ update (found all?, schema changed?, observations not found!):",successful[0], successful[1], len(successful[2].state)


		#If bootstrap schema updated, return
		if successful[1]:
			self.current_schema = None
			return 0.5

		if (prev_state == None):
			self.current_schema = None
			return 1

		all_expected_states  = prev_state.union(self.current_schema.postconditions.union(self.current_schema.associated_observations))
		print "All obbservations:\n", all_expected_states.to_string()


		new_states_found = all_expected_states.complement(self.ws) #difference
		print "New observation Found:\n",new_states_found.to_string()

		lost = self.ws.complement(prev_removed)


		f = Schema(self)
		#f =  self.current_schema.copy()
		f.action = self.current_schema.action.copy()
		self.emit("connect_action", f.action)

		if self.current_schema.generalised:
			for p in f.action.props.keys():
				f.action.props_var[p] = None
			for c in f.action.coords.concrete_coords.keys():
				f.action.coords.variable_coords[c] = None
		print "F.action :::::", f.action.to_string()
		f.associated_observations = new_states_found.copy()
		for o in lost.state:
			if not o.self_flag:
				f.associated_preconditions.add_observation(o)

		#find ground truth coordinates used in action, if no cordinates then take coordinates of Propio
		coords = self.current_schema.action.coords.copy()
		coords_included = True
		if len(coords.concrete_coords.keys()) < 1 :
			coords_included = False
			for o in self.ws.state:
				if o.name == "propio":
					print "Propio coords are added:", o.coords.to_string()
					coords = o.coords.copy(); break

		# If ws observation has matches ground truth coordinates add it to post/pre-conditions
		added = []
		for o1 in self.ws.state:
			found  = False
			if o1 in prev_state.state:
				found = True
				print "Pre/Post match & coords in action 1:", o1.to_string(),  o1.coords.equals(coords)
				if o1.coords.equals(coords):
					f.postconditions.add_observation(o1)
					if not o1.self_flag:
						f.preconditions.add_observation(o1)
				elif len(o1.coords.concrete_coords.keys()) < 1:
					f.associated_observations.add_observation(o1)
					if not o1.self_flag:
						f.associated_preconditions.add_observation(o1)
				added.append(o1.id)
			else:
				for o2 in prev_state.state:
					if o2.id in added:
						continue
					if o1.similar(o2) and o1.id == o2.id:
						found = True
						print "Pre/Post similar & coords in action 1:", o1.to_string(),  o2.coords.equals(coords)
						if o1.coords.equals(coords):
							#print "Current: Observation coords matching with sample coords added as associated:", o.id
							f.postconditions.add_observation(o1)
							if not o2.self_flag:
								f.preconditions.add_observation(o2)
						elif o2.coords.equals(coords):
							#print "Previous: Observation coords matching with sample coords added as associated:", o.id
							f.associated_observations.add_observation(o1)
							if not o2.self_flag:
								f.associated_preconditions.add_observation(o2)
						else:
							#print "Observation with not matching sample coords added as associated:", o.id
							f.associated_observations.add_observation(o1)
							if not o2.self_flag:
								f.associated_preconditions.add_observation(o2)
						added.append(o2.id);break
			if not found:
				#print "Observation not occurred previously:", len(f.associated_observations.state), o1.to_string()
				if o1.coords.equals(coords):
					#print "@@@@COORDS not match"
					f.postconditions.add_observation(o1); continue
				f.associated_observations.add_observation(o1)


		# Remove associated observations already in concrete
		for o in f.postconditions.state:
			f.associated_observations.remove_observation(o)
		for o in f.preconditions.state:
			f.associated_preconditions.remove_observation(o)


		#f.parent_schemas = list(self.current_schema.parent_schemas)
		#f.parent_schemas.append(self.current_schema.id)
		f.added_ID = int(self.total_executions)

		#Change ends here
		print "\n**********Schema****************\n", f.to_string()


		# Find disappeared observations
		disappeared = WorldState()
		for o in prev_state.state:
			found = False
			for o2 in self.ws.state:
				if o2.similar(o):
					found = True;break
			if not found:
				if o.coords.equals(coords):
					print " in disappear:",o.id, o in f.preconditions.state, o in f.associated_preconditions.state, o.self_flag
					if (o in f.preconditions.state or not o.self_flag):
						print "Adding Dissappeared observation:", o.to_string()
						disappeared.add_observation(o)

		removing = []
		for i in self.current_schema.parent_schemas:
			if self.current_schema.generalised:
				break
			s_parent = self.get_schema_from_id(i)
			for o in f.preconditions.union(f.associated_preconditions).state:
				found = True
				for o1 in s_parent.preconditions.state:
					found = False
					if o.id == o1.id and not o1.equals(o):
						print "Adding observation in removing from Pre:",o.to_string(),  (coords_included and s_parent.action.coords.get_coords().keys())
						if coords_included and len(s_parent.action.coords.get_coords().keys()) > 0:
							removing.append(o.id)
			for o in f.postconditions.union(f.associated_observations).state:
				found = False
				for o1 in s_parent.postconditions.union(s_parent.associated_observations).state:
					if o.id == o1.id:
						if not o1.equals(o):
							print "Adding observation in removing from Post:",o.to_string(), o1.to_string(),(coords_included and s_parent.action.coords.get_coords().keys())
							found = True
							if coords_included and len(s_parent.action.coords.get_coords().keys()) > 0:
								removing.append(o.id); break
						else:
							found = True; break
					if o.name == o1.name and o.self_flag:
						found = True
				if not found and o.self_flag:
					print "Observation not found in parent schemas:",o.to_string()
					removing.append(o.id)
		for o in f.preconditions.state:
			if o.id in removing:
				f.preconditions.remove_observation(o)
		for o in f.postconditions.state:
			if o.id in removing:
				f.postconditions.remove_observation(o)

		f.disappeared_observations = disappeared.copy()

		print "@@@@@@@@@@@@@@New Schema to be tested@@@@@@@@@\n", f.to_string()
		if (not successful[0]) and self.current_schema.generalised:
			print "Failed generalised schema to be added in the list"
			self.current_schema.add_failed_schema(f)

		if (len(new_states_found.state)> 0 or len(f.disappeared_observations.state) > 0 ) and len(f.preconditions.union(f.associated_preconditions).state) > 0: #or Test2 or len(successful[2].state) >0 or Test3:
			match_found = False; generalised_match =  False
			for s in self.schemas:
				if not s.generalised:
					if s.preconditions.union(s.associated_preconditions).satisfies(f.preconditions.union(f.associated_preconditions)) and s.postconditions.union(s.associated_observations).satisfies(f.postconditions.union(f.associated_observations)) and s.disappeared_observations.satisfies(f.disappeared_observations) and s.action.equals(f.action):
						print "Similar schema already exists:", s.id
						match_found = True; break
				else:
					s.set_vars_from_state(f.preconditions)
					print "Test to match similar in generalised schema:",s.id, s.preconditions.union(s.associated_preconditions).equivalents(f.preconditions.union(f.associated_preconditions)), s.postconditions.union(s.associated_observations).equivalents(f.postconditions.union(f.associated_observations)), s.disappeared_observations.equivalents(f.disappeared_observations)
					if s.preconditions.union(s.associated_preconditions).equivalents(f.preconditions.union(f.associated_preconditions)) and s.postconditions.union(s.associated_observations).equivalents(f.postconditions.union(f.associated_observations)) and s.disappeared_observations.equivalents(f.disappeared_observations) and s.action.equals(f.action):
						print "\nSimilrity btw New_schema and Generalised Schema %i is found:"%s.id,"\n", s.to_concrete_string()
						match_found = True; generalised_match = True; break

			if match_found:
				print "Match found %i, new schema will not be added into memory"%s.id
				#Associated Observations confirmed from current schema will be added into concrete
				if not (self.current_schema.generalised or generalised_match):
					for o in self.current_schema.associated_observations.state:
						if (o in f.associated_observations.state) and (o in self.ws.state):
							f.postconditions.add_observation(o)
							f.associated_observations.remove_observation(o)
					for o in self.current_schema.associated_preconditions.state:
						if (o in f.associated_preconditions.state) and (o in prev_removed.state):
							f.preconditions.add_observation(o)
							f.associated_preconditions.remove_observation(o)
					print "@@@@@@@@@@@@@@Updated Schema@@@@@@@@@\n", f.to_string()
					exists = False
					for s2 in self.schemas:
						if s2.preconditions.union(s2.associated_preconditions).satisfies(f.preconditions.union(f.associated_preconditions)) and s2.postconditions.union(s2.associated_observations).satisfies(f.postconditions.union(f.associated_observations)) and s2.disappeared_observations.satisfies(f.disappeared_observations):
							if s2.id == self.current_schema.id:
								continue
							print "Updated schema already in memory:", s2.id
							exists = True; break
					if len(self.current_schema.preconditions.state) > 0 and not exists:
						if s2.id == self.current_schema.id:
							f.added_ID = int(self.current_schema.added_ID)
							f.execution_ID += self.current_schema.execution_ID
							print "F execution ID:", f.execution_ID
						f.id = self.current_schema.id
						if len(f.parent_schemas):
							f.parent_schemas.remove(self.current_schema.id)
						self.schemas[self.current_schema.id] = f
						with open(self.t_d, "a") as file:
							file.write("\n@@@@@@@@@@@@@@@@@@Schema updated from@@@@@@@@@@@@@@@@@@@@\n %s \n to new Schema \n %s"%(self.current_schema.to_string(), f.to_string()))
					if not s.generalised:
						states = s.associated_observations.union(s.postconditions)
					else:
						states = f.associated_observations.union(s.postconditions)
					ids = [i.id for i in states.state]
					for o in self.ws.state:
						if not o.id in ids or s.generalised:
							continue
						#print "OIDs and keys:", o.id, s.id, self.observation_in_schemas[o.id].first
						if self.observation_in_schemas.has_key(o.id):
							if not(s.id in self.observation_in_schemas[o.id].first):
								#print "Adding o.id as in used schema 1:", o.id, s.id, self.observation_in_schemas[o.id].second, self.observation_id_occurrences(o)
								self.observation_in_schemas[o.id].second +=1.0
								self.observation_in_schemas[o.id].first.append(s.id)
							else:
								print "Adding observation in schema count 1:", o.id, self.observation_in_schemas[o.id].second, self.observation_id_occurrences(o.id)
								self.observation_in_schemas[o.id].second +=1.0
						else:
							#print "Adding new o.id as in used schema 1:", o.id, s.id, self.observation_in_schemas[o.id].second, self.observation_id_occurrences(o)
							self.observation_in_schemas[o.id] = Pair([s.id], 1.0)
				print "Generalisation updated Schema code:",self.generaliser.assimilate(f, self.schemas, True)
				self.current_schema = None; return 2
			else:
				print "New schema added in memory"
				f.added_ID = int(self.total_executions)
				self.add_schema(f);
				#Adding Child schemas
				child = []; parent = []
				for s in self.schemas:
					states = s.associated_observations.union(s.postconditions)
					ids = [i.id for i in states.state]
					for o in self.ws.state:
						if not o.id in ids  or s.generalised:
							continue
						if self.observation_in_schemas.has_key(o.id):
							if not(s.id in self.observation_in_schemas[o.id].first):
								print "Adding o.id as in used schema 2:", o.id, s.id, self.observation_in_schemas[o.id].second, self.observation_id_occurrences(o.id)
								self.observation_in_schemas[o.id].second +=1.0
								self.observation_in_schemas[o.id].first.append(s.id)
						else:
							print "Adding new o.id as in used schema 2:", o.id, s.id, self.observation_id_occurrences(o.id)
							self.observation_in_schemas[o.id] = Pair([s.id], 1.0)

					if s.id == f.id or len(s.preconditions.state) == 0:
						continue
					f_post = f.associated_observations.union(f.postconditions)
					found_post = self.remove_ignored_preconditions(f_post)
					s_post = s.associated_observations.union(s.postconditions); self.remove_ignored_preconditions(s_post)
					if f.preconditions.union(f.associated_preconditions).satisfies(s_post, f.action.coords.concrete_coords.keys()):
						if f.action.equals(s.action, f.action.coords.concrete_coords.keys()):
							continue
						if not (f.id in s.child_schemas and f.id in s.parent_schemas):
							s.child_schemas.append(f.id); parent.append(s.id)
						if not (s.id in f.parent_schemas and s.id in f.parent_schemas):
							f.parent_schemas.append(s.id)
						continue
					if s.preconditions.union(s.associated_preconditions).satisfies(found_post, f.action.coords.concrete_coords.keys()):
						if f.action.equals(s.action, f.action.coords.concrete_coords.keys()):
							continue
						if not (s.id in f.parent_schemas and s.id in f.parent_schemas):
							f.child_schemas.append(s.id); child.append(s.id)
						if not (f.id in s.child_schemas and f.id in s.parent_schemas):
							s.parent_schemas.append(f.id)
						continue
				sig = self.generaliser.assimilate(f, self.schemas, False); print "Generalisation code:",sig
				#print "Last Schemas Test:", len(self.schemas[-1].associated_observations.state)
				self.current_schema = None
				return 3
			self.current_schema = None; return 4
		else:
			print "*****Condition to create new schema not matched*****\n"
			match_found = False;
			if successful[0]:
				states = f.associated_observations.union(f.postconditions)
				ids = [i.id for i in states.state]
				for o in self.ws.state:
					if not o.id in ids:
						print "Id not in schema:", o.id
						continue
					if self.observation_in_schemas.has_key(o.id):
						if not (self.current_schema.id in self.observation_in_schemas[o.id].first):
							print "Addin o.id as in used schema 3:", o.id, self.current_schema.id, self.observation_in_schemas[o.id].second, self.observation_id_occurrences(o)
							self.observation_in_schemas[o.id].second += 1.0
							self.observation_in_schemas[o.id].first.append(self.current_schema.id)
						else:
							self.observation_in_schemas[o.id].second += 1.0
					else:
						print "Addin new o.id as in used schema 3:", o.id, self.current_schema.id, self.observation_id_occurrences(o)
						self.observation_in_schemas[o.id] = Pair([self.current_schema.id], 0.0)
			self.current_schema = None; return 5

	def tolerance(self, a, b):
		"""Check if value is within tolerance limit"""
		#print abs(a-b)
		return abs(a-b)

	def get_excited_schemas(self, state):
		"""Returns list of Pairs containg schemas"""
		if (state == None):
			state = self.ws
		pairs = self.get_excited_schema_pairs(state)
		excited_schemas = []
		for p in pairs:
			excited_schemas.append(p.first)
		return excited_schemas

	def get_excite_all(self, state):
		"""Returns excitations of all excited schemas"""
		if (state == None):
			state = self.ws
		pairs = self.get_excited_schema_pairs(state);
		excitation = []
		for p in pairs:
			excitation.append(p.second)
		return excitation

	def get_excited_schema(self, state):
		"""Returns most excited schema for the given state"""
		if (state == None):
			state = self.ws
		excited_schemas = self.get_excited_schema_pairs(state)
		most_excited = excited_schemas[0].first
		return most_excited

	def get_excite(self, s, state):
		"""Retruns excitaion of the given schema for given state"""
		excitation = self.excitation_calculator.get_excitation(s, state)
		return excitation

	def get_excited_schema_pairs(self, state):
		"""Returns list of schemas, excited for given state"""
		if(state == None):
			state = self.get_current_ws()
		excited_schemas = []
		for s in self.schemas:
			excitation = self.excitation_calculator.get_excitation(s, state)
			if excitation > 0:
				p = Pair(s, excitation); excited_schemas.append(p)
		newlist = sorted(excited_schemas, key=lambda k: k.second, reverse=True)
		return newlist


	def execute_excited_schema(self, state):
		"""Executes excited schema for given state, Returns excitation of the excited schema"""
		if(state == None):
			state = self.ws
		excited_schemas = self.get_excited_schema_pairs(state)
		most_excited = excited_schemas[0].first
		excitation = excited_schemas[0].second
		self.execute(most_excited)
		return excitation


	def get_excited_agent(self, ws, record= False):
		wsc = ws.copy()
		self.remove_ignored_preconditions(wsc)
		#print "WS @ get_excited_agent:\n", wsc.to_string()
		highest = 0; top =0; excited_schemas = []; excitations = {}
		for s in self.schemas:
			exc = self.excitation_calculator.get_excitation(s, ws, record)
			pair = Pair(s, exc); s.excitation = float(exc)
			#print "Schema excitation found:", s.id, exc, s.excitation, self.excitation_calculator.m,"\n"
			excited_schemas.append(pair); excitations[s.id] = s.excitation

		excited_schemas = sorted(excited_schemas, key=lambda excited_schemas:excited_schemas.second, reverse=True)
		top = excited_schemas[0].first.id; top_checked = False
		excited_chains = []; chain_excitation = []

		for chainx in self.chains:
			ex = 0.0; s_exci = 0.0; chain_excitations = []
			diff = len(ws.difference(self.schemas[chainx.sequence[0]].postconditions.union(self.schemas[chainx.sequence[0]].associated_observations.union(self.schemas[chainx.sequence[0]].disappeared_observations))).state)
			s_pre = self.schemas[chainx.sequence[0]].preconditions.union(self.schemas[chainx.sequence[0]].associated_preconditions)
			s_post = self.schemas[chainx.sequence[-1]].postconditions.union(self.schemas[chainx.sequence[-1]].associated_observations)
			if not self.schemas[chainx.sequence[0]].generalised:
				if (not wsc.satisfies(s_pre)) or ws.satisfies(s_post) or excitations[chainx.sequence[0]]==0.0: #If first schema of chain doesn't satisfy WS then Exc =0
					print "@get_excited_agent Chain doestn't satisfies WS2: ", chainx.sequence, excitations[chainx.sequence[0]], wsc.satisfies(s_pre),ws.satisfies(s_post)
					ex = 0.0; chainx.excitation = ex; excited_chains.append(Pair(chainx, ex)); continue
			else:
				if (not wsc.equivalents(s_pre)) or ws.equivalents(s_post) or excitations[chainx.sequence[0]]==0.0: #If first schema of chain doesn't satisfy WS then Exc =0
					print "@get_excited_agent Chain doestn't equivalents WS2: ", chainx.sequence, excitations[chainx.sequence[0]], wsc.equivalents(s_pre), ws.equivalents(s_post)
					ex = 0.0; chainx.excitation = ex; excited_chains.append(Pair(chainx, ex)); continue
			for C in range(0, len(chainx.sequence)-1):
				#exm = excitations[C]; s_exci +=exm; chain_excitations.append(excitations[C])
				#chain_excitation.append(excitations[C])
				diff += len(self.schemas[chainx.sequence[C]].preconditions.union(self.schemas[chainx.sequence[C]].associated_preconditions).difference(self.schemas[C+1].postconditions.union(self.schemas[C+1].associated_observations.union(self.schemas[C+1].disappeared_observations))).state)
			#ex = (chain_excitation[-1]*diff)/len(chain_excitation)
			ex = diff/ float(2*len(chainx.sequence))
			if ex > 1.0: ex = 1.0
			tau = 0.0; ex2 = 1.0
			if len(chainx.execution_ID) > 1 and self.total_executions:
				dif = []; excs = []; t = self.total_executions
				for i in range(0, len(chainx.execution_ID)):
					e = chainx.execution_ID[i]/float(t)
					excs.append(e)
					t -=1
				tau = (stc.mean(excs) +stc.variance(excs))
				ex2 = math.e**(-1.1*tau)
			ex = ex2*ex
			ex = ex*(1+ chainx.successes) /(1+ chainx.activations); chainx.excitation = float(ex)
			print "chain & excitation############: ",chainx.sequence, diff, chainx.successes, chainx.activations,chainx.execution_ID, tau, ex2, chainx.excitation, len(self.chains)#, excited_chains
			excited_chains.append(Pair(chainx, ex))
		excited_chains= sorted(excited_chains, key=lambda excited_chains:(excited_chains.second,len(excited_chains.first.sequence)), reverse=True)
		if len(excited_chains) > 0 and (excited_chains[0].second >= excited_schemas[0].second):
			return excited_chains
		else:
			for s in self.schemas:
				s.set_vars_from_state(wsc)
			return excited_schemas

	def execute_excited_agent(self, ws=None, exci_agent = None, record = False):
		"""Executes the excited agent for given state"""
		#self.total_executions +=1
		if ws == None:
			print "Empty WS @execute_excited_agent"
			agent = self.get_excited_agent(self.ws, True)
		else:
			if exci_agent == None:
				print "WS @execute_excited_agent with none agent"
				agent = self.get_excited_agent(ws, record)
			else:
				print "Taking provided as excited agent"
				agent = exci_agent
		if str(type(agent[0].first)) == "<class 'Schema.Schema'>":
			print "Executing Schema: ", agent[0].first.id
			s = self.get_schema_from_id(agent[0].first.id)
			self.execute(s, False); self.total_executions +=1
		elif str(type(agent[0].first)) == "<class 'Chain.Chain'>":
			#self.current_chain = self.get_chain_from_sequence(agent[0].first)
			self.current_chain = agent[0].first.copy()
			self.current_chain.activations +=1
			print "Excited chain: ", self.current_chain.sequence, "  ; activations:",self.current_chain.activations, " Having excitation: ", agent[0].second, " and executions:",agent[0].first.execution_ID
			agent[0].first.execution_ID.append(self.total_executions)
			self.total_executions +=1
			for c in self.current_chain.sequence:
				s = self.get_schema_from_id(c)
				#if self.ws.satisfies(s.postconditions):
				print "Executing chain schema: ", s.id
				#s.action.execute()
				self.execute(s, False); success = self.current_chain.successes
				if (c != self.current_chain.sequence[-1]) and (success < 5):
					print "Updating state @ execute_excited_agent"
					self.emit("update_state")
					if self.current_chain == None:
						return
				else:
					print "Schema in chain executed without state check:",s.id
		else:
			print "Invalid agent found or no excited agent found"

	def execute(self, s, solve = True):
		"""Executes given schema
		If current state matches Schema preconditions then schema is executed directly
		If doesn't matches then goal is achieved"""
		ws_minus_ignored = self.ws.copy()
		self.remove_ignored_preconditions(ws_minus_ignored)
		#if s.generalised:
		#	s.set_vars_from_state(ws_minus_ignored)
		self.current_schema = s
		if ws_minus_ignored.satisfies(self.current_schema.preconditions.union(self.current_schema.associated_preconditions)):
			print "Current state satisfies preconditions"
			self.current_schema.execute(); self.last_executed_id = int(self.current_schema.id)
			return 1
		#elif (not ws_minus_ignored.satisfies(self.current_schema.preconditions.union(self.current_schema.associated_preconditions)) and solve):
		#	print "Achieving goal in execute:", solve, ws_minus_ignored.satisfies(self.current_schema.preconditions.union(self.current_schema.associated_preconditions))
		#	goal = self.achieve_goal2(self.current_schema.postconditions.union(self.current_schema.associated_observations), [self.current_schema.id], self.current_schema.disappeared_observations)
		#	if not goal:
		#		print "Target chain not found, executing excited action"
		#		self.execute(s, False)
		#	else:
		#		if not s.id in self.goal_chain.sequence:
		#			s.execution_ID.append(int(self.total_executions))
		#			s.activations +=1
		#			#pass
		#		self.goal_chain = None
		#		print "Target Achieved with a chian"
		#	return 2
		elif (not solve):
			print "Executing schema no %i without pre-state check"%self.current_schema.id
			self.current_schema.execute(); self.last_executed_id = int(self.current_schema.id)
			return 3
		return 4

	def get_average_excitement(self, state):
		"""Returns average excitation of excited schemas"""
		if(state == None):
			state = self.ws
		total_excitation = 0
		excited_schemas = self.get_excited_schema_pairs(state)
		for p in excited_schemas:
			total_excitation += p.second
		return total_excitation / self.get_total_schemas()

	def generalise(self, s):
		"""Generalises the given schema; returns code from genralisation program"""
		res = self.generaliser.assimilate(s, self.schemas)
		return res

	def take_action(self, a):
		"""Create schema with given action and execute it"""
		self.current_schema = self.get_or_create_schema(WorldState(), a, WorldState(), True) # Removed self.ws from pre
		if(self.current_schema.get_probability() < 0.8 and self.current_schema.activations > 100 and not self.current_schema.is_synthetic() and self.last_action != None):
			self.ws.add_observation(self.last_action)
			self.current_schema = self.get_or_create_schema(self.ws, WorldState(), True)
		predicted_world_state = self.current_schema.postconditions.get_predictions()
		self.current_schema.execute()



	def execute_this_schema(self, this_schema):
		"""Executes given schema"""
		self.execute(this_schema)
		return True

	def execute_id(self, id):
		"""Executes schema having given ID"""
		self.current_schema = self.schemas[id]
		self.current_schema.execute()


	def achieve_target (self, tar, exclu):
		"""Achieve target state (tar) using single schema
		Find schema matching postconditions with target and execute it"""
		L = []; highest = 0; match = 0; idno = None
		print "Traget received:", tar.to_string()
		for m in range(0, len(self.schemas)):
			if m == exclu:
				continue
			sc = self.get_schema_from_id(m); match = 0;
			#print "Length:"
			#print "ID: %i"%m," Postconditions satisfies target? ",(sc.postconditions.equivalents(tar))
			if ((not sc.generalised) and (sc.postconditions.equivalents(tar))):
				print "ID: %i"%m," Postconditions satisfies target"
				L.append(sc.id)
				for o in tar.state:
					for o2 in sc.postconditions.state:
						if (o.name == o2.name):
							prop2 = o2.get_properties()
							prop = o.get_concrete_properties()
							for p in prop.keys():
								v2 = prop2[p]
								v1 = prop[p]
								if (v2 != None and  v1 == v2):
									match += 1
				if (match > highest):
					highest = match; idno = sc.id
				L.append(match); L.append(highest); L.append(idno);
		n = self.get_schema_from_id(idno)
		print "Solving target by schema: ", n.id, " having highest matches: ", highest
		n.execute()
		return idno

	def achieve_goal(self, target_state, excluded = None, lost = None, resolving_target = False):
		"""Achieve target state from current state by creating chains"""
		wsc = self.ws.copy(); self.remove_ignored_preconditions(wsc)
		sequence = self.find_path3(wsc, target_state, excluded, lost, resolving_target)
		if(len(sequence) == 0):
			return False
		for i in range(0, len(sequence)):
			s = sequence[i]
			if (self.schemas[s].generalised and not resolving_target):
				wsc = self.ws.copy()
				self.remove_ignored_preconditions(wsc)
				self.schemas[s].set_vars_from_state(wsc)
			if (not self.ws.satisfies(self.schemas[s].preconditions)):
				return self.achieve_goal(target_state)
			self.schemas[s].execute()
		return True


	def achieve_goal2(self, target_state, excluded = None, lost = None, resolving_target = False):
		wsc = self.ws.copy(); self.remove_ignored_preconditions(wsc)
		path = self.find_path3(wsc, target_state, excluded, lost)
		if len(path) <2:
			return False
		else:
			print "Achieving target with sequence:", path
			C = Chain(); C.sequence = path
			path2 = self.get_chain_from_sequence(C)
			path2.execution_ID.append(self.total_executions)
			for i in range(0, len(path2.sequence)):
				if i ==0:
					start = wsc
				else:
					start = self.schemas[s].postconditions.copy()
					start.state += list(self.schemas[s].associated_observations.copy().state)
				s = path[i]
				if self.schemas[s].generalised:
					self.schemas[s].set_vars_from_state(start)
				print "Achieving goal with schema %i in the chain"%self.schemas[s].id, path
				self.schemas[s].execute()
			self.goal_chain = path2
			return True

	def execute_sequence_step(self, sequence, target_state):
		"""Execute sequence of schemas, Not used in current system"""
		if (len(sequence.state) == 0):
			return sequence.copy()
		s = sequence[0]
		if (self.schemas[s].generalised):
			self.remove_ignored_preconditions(self.ws)
			self.schemas[s].set_vars_from_state(self.ws)
		if (not self.ws.satisfies(self.schemas[s].preconditions)):
			target = target_state.copy()
			return self.find_path(self.ws, target, [], False)
		self.schemas[s].execute();
		remaining_sequence = sequence.copy()
		remaining_sequence.remove(s)
		return remaining_sequence


	def find_path(self, state, tar, exclude, resolve = False):
		"""Finds the path from given state to target state by creating chains
		Returns list containg schema IDS
		This is orignal version of function"""
		destination = -1; pathschemas = [];
		pathschemas = list(self.schemas)
		distances = {}; sequence = []
		for i in range(0, len(pathschemas)):
			if(pathschemas[i].generalised and not resolve):
				self.remove_ignored_preconditions(state)
				pathschemas[i].set_vars_from_state(state)
			if (state.satisfies(pathschemas[i].preconditions)):
				distances[i] = 0
			else:
				distances[i] = -1
		previous = {}; q = {}
		for i in range(0, len(pathschemas)):
			q[i] = pathschemas[i].copy()
			previous[i] = -1
		#for ex in exclude:
		if len(exclude)> 0:
			q[exclude] = None
		q_length = len(pathschemas); u = -1; u_p = None
		target = tar#.copy()
		while(q_length > 0):
			#print "*******************Attempt: %i****************** "%q_length
			shortest_distance = -1
			for i in range(0, len(pathschemas)):
				if (distances[i] == -1 ):
					continue
				if ((distances[i] < shortest_distance or shortest_distance == -1) and q[i] != None):
					shortest_distance = distances[i]
					#print "Distance: ",distances[i], shortest_distance, i
					u = i
					u_p = q[i].copy()
			#print "first distance:", u , u_p.id
			if (shortest_distance == -1):
				break
			q[u] = None
			q_length -= 1
			if (pathschemas[u].generalised and not resolve):
				self.remove_ignored_preconditions(target)
				#print "Target: ", target.to_string()
				pathschemas[u].set_vars_from_state(target)
			if (pathschemas[u].postconditions.satisfies(target)):
				destination = u
				break
			for i in range(0, len(pathschemas)):
				if (q[i] == None):
					continue
				if (q[i].generalised and not resolve):
					self.remove_ignored_preconditions(u_p.postconditions)
					q[i].set_vars_from_state(u_p.postconditions)
				if (u_p.postconditions.satisfies(q[i].preconditions)):
					neighbour_distance = 0.001 + 1 - u_p.postconditions.get_probability()
				else:
					continue
				alt = shortest_distance + neighbour_distance
				if (alt < distances[i] or distances[i] == -1):
					distances[i] =alt
					previous[i] = u
		if (destination == -1):
			#print "No path found for:"
			return []
		n = destination
		while (n != -1):
			if not(n in sequence):
				sequence = [n] + sequence
				n = previous[n]
		if len(sequence) > 1:
			self.add_chain(sequence)
			return sequence
		else:
			return []


	def find_path2(self, state, target, exclude = [], resolve = False):
		"""Developed version of find_path function
		Finds the path from given state to target state by creating chains
		Returns list containg most reliable schema IDS"""
		pathschemas = list(self.schemas)
		start = None; distances = []; probability = 0.0; starts = []
		for i in range(0, len(pathschemas)):
			if(pathschemas[i].generalised and not resolve):
				self.remove_ignored_preconditions(state)
				pathschemas[i].set_vars_from_state(state)
			if (state.equals(pathschemas[i].preconditions)): #and pathschemas[i].get_probability() > probability:
				if pathschemas[i].get_probability() >=probability:
					probability = pathschemas[i].get_probability()
					starts.append(i)

		if len(starts) == 0:
			print "No direct path to target:\n", target.to_string()
			return []
		print "Start found for the target:", starts
		tar = target.copy(); self.remove_ignored_preconditions(tar)
		paths = []

		probability = 0
		for s in starts:
			start = self.get_schema_from_id(s)
			#print "**Finding chain with start:**", start.id

			if start.postconditions.equals(target):
				paths.append([start.id])
				continue

			if not start.generalised:
				excluded = [int(start.id)]; excluded += exclude
			else:
				excluded = list(exclude)

			for i in range(0, len(pathschemas)):
				current_chain = [start.id]
				if pathschemas[i].id in excluded or len(pathschemas[i].preconditions.state) == 0:
					continue
				start_post = start.postconditions.copy(); self.remove_ignored_preconditions(start_post)
				if pathschemas[i].generalised:
					pathschemas[i].set_vars_from_state(start_post) ##Instatntaite generelised schema from last postconditions

				if pathschemas[i].preconditions.equals(start_post):
					current_chain.append(pathschemas[i].id); ignore = list(excluded)
					if not pathschemas[i].generalised:
						ignore.append(pathschemas[i].id)
					start_2 = pathschemas[i].copy(); found = False

					if start_2.postconditions.equals(target):
						found = True; paths.append(current_chain); break
					else:
						while not start_2.postconditions.equals(target):
							found = False; probability = -1

							if len(current_chain) > 5:
								break
							for j in range(0, len(pathschemas)):
								if pathschemas[j].id in ignore:
									continue
								posts = start_2.postconditions.copy(); self.remove_ignored_preconditions(posts)
								if pathschemas[j].generalised:
									pathschemas[j].set_vars_from_state(posts)
								#print "Testing second schema:",start_2.id, j,pathschemas[j].preconditions.satisfies(posts),pathschemas[j].postconditions.satisfies(target),pathschemas[j].get_probability()#,"\n", posts.to_string(), "\n vs\n", pathschemas[j].preconditions.to_string()
								if pathschemas[j].preconditions.equals(posts) and pathschemas[j].get_probability() > probability:
									probability = pathschemas[j].get_probability()
									start_2 = pathschemas[j].copy(); found = True
							if not found:
								print "Chain not terminated to target:", current_chain
								break
							else:
								if not start_2.generalised:
									ignore.append(start_2.id)
								current_chain.append(start_2.id)
					if found:
						#print "Chain found:", current_chain
						paths.append(current_chain)
		if len(paths) > 0:
			max_prob = 0.0; reliable = None
			for path in paths:
				prob = 0.0
				for id in path:
					s = self.get_schema_from_id(id)
					prob += s.get_probability()
					#print "S.probability::::",s.id, prob, s.postconditions.to_string()
				#print "Chain.probability::::",path, (prob+len(path))/(prob*len(path))
				if (prob+len(path))/(prob*len(path)) > max_prob:
					max_prob = float((prob+len(path))/(prob*len(path)))
					reliable = list(path)
			print "Chain found with highest reliabality:", reliable, max_prob," of all chains:", len(paths)
			self.add_chain(reliable)
			return reliable
		else:
			return []



	def find_path3(self, state, target, exclude, lost = None, resolve = False):
		"""Developed version of find_path function
		Finds the path from given state to target state by creating chains
		Returns list containg most reliable schema IDS"""
		pathschemas = list(self.schemas)
		start = None; distances = []; probability = 0.0; starts = []; ends = []
		tar = target.copy(); self.remove_ignored_preconditions(tar)
		ws = self.ws.copy(); self.remove_ignored_preconditions(ws)
		for i in range(0, len(pathschemas)):
			#print "~~~~~~~~~HERE~~~~~~~~~", pathschemas[i].id,pathschemas[i].generalised, resolve, inspect.stack()[1][3],"\n"
			if len(pathschemas[i].preconditions.union(pathschemas[i].associated_preconditions).state) ==0:
				continue
			if(pathschemas[i].generalised and not resolve):
				self.remove_ignored_preconditions(state)
				pathschemas[i].set_vars_from_state(state)

			if not pathschemas[i].action.coords.concrete_coords.keys() > 0:
				#print "Finding Start End with No coords schema:", pathschemas[i].id
				if state.equivalents(pathschemas[i].preconditions.union(pathschemas[i].associated_preconditions)): #and pathschemas[i].get_probability() > probability:
					if not i in starts:
						starts.append(i)
				if(pathschemas[i].generalised and not resolve):
					self.remove_ignored_preconditions(tar)
					pathschemas[i].set_vars_from_state(tar)
				if pathschemas[i].postconditions.union(pathschemas[i].associated_observations).equivalents(tar): #and pathschemas[i].get_probability() > probability:
					if lost != None and pathschemas[i].disappeared_observations.equivalents(lost):
						if not i in ends:
							ends.append(i)
					else:
						print "Lost not equals1:", pathschemas[i].id,lost
			else:
				#print "\nTesting start condition match:\n",pathschemas[i].preconditions.union(pathschemas[i].associated_preconditions).to_concrete_string(),"\n",state.to_string(),"\n",state.satisfies(pathschemas[i].preconditions.union(pathschemas[i].associated_preconditions)), pathschemas[i].id, "\n"
				if not i in exclude:
					if state.satisfies(pathschemas[i].preconditions.union(pathschemas[i].associated_preconditions)): #and pathschemas[i].get_probability() > probability:
						#print "Adding in start:", i
						if not i in starts:
							starts.append(i)
				if(pathschemas[i].generalised and not resolve):
					self.remove_ignored_preconditions(tar)
					#print "Sending Fro Target instantiation"
					pathschemas[i].set_vars_from_state(tar)
				if pathschemas[i].postconditions.union(pathschemas[i].associated_observations).satisfies(tar): #and pathschemas[i].get_probability() > probability:
					#print "Appending ends:",(pathschemas[i].postconditions.union(pathschemas[i].associated_observations).satisfies(tar)),tar.to_string(), i
					if lost != None and pathschemas[i].disappeared_observations.equivalents(lost):
						if not i in ends:
							ends.append(i)
					else:
						print "Lost not equals2:", pathschemas[i].id, lost

		if len(starts) == 0 or len(ends) == 0:
			print "No direct path:", starts, ends
			return []

		print "Starts and Ends found initailaly:", starts, ends

		remove_start = []; remove_end = []
		for c in self.chains:
			chain_found = False
			for start in starts:
				if start == c.sequence[0]:
					for end in ends:
						if end == c.sequence[-1]:
							print "Chain already exists:", c.sequence
							found = True; break
					if chain_found:
						remove_end.append(end); break
			if chain_found:
				remove_end.append(start)

		for r_s in remove_start:
			starts.remove(r_s)
		for r_e in remove_end:
			ends.remove(r_e)

		print "Starts & Ends updated:", starts, ends

		paths = []
		probability = 0
		for s1 in starts:
			if s1 in ends:
				paths.append([s1])
			for c1 in pathschemas[s1].child_schemas:
				current_chain = [s1]; found = False;
				if c1 in ends and (not c1 in current_chain):
					current_chain.append(c1);
					if not len(current_chain)> 4:
						if not self.schemas[current_chain[0]].preconditions.union(self.schemas[current_chain[0]].associated_preconditions).satisfies(self.schemas[current_chain[0]].postconditions.union(self.schemas[current_chain[-1]].associated_observations)):
							paths.append(current_chain)
							#print "Current chain:", current_chain, c1
							found = True; continue
				#print "@Current_chain:", current_chain, c1
				for c2 in pathschemas[c1].child_schemas:
					found = False; current_chain.append(c1)
					if c2 in ends and (not c2 in current_chain):
						current_chain.append(c2);
						if not len(current_chain)> 4:
							if not self.schemas[current_chain[0]].preconditions.union(self.schemas[current_chain[0]].associated_preconditions).satisfies(self.schemas[current_chain[0]].postconditions.union(self.schemas[current_chain[-1]].associated_observations)):
								paths.append(current_chain)
								#print "Current chain1:", current_chain, c1, c2
								current_chain= [s1]; found = True; continue
					#print "@Current_chain1:", current_chain, c2
					for c3 in pathschemas[c2].child_schemas:
						found =  False
						current_chain.append(c2)
						if c3 in ends and not c3 in current_chain:
							current_chain.append(c3);
							if not len(current_chain)> 4:
								if not self.schemas[current_chain[0]].preconditions.union(self.schemas[current_chain[0]].associated_preconditions).satisfies(self.schemas[current_chain[0]].postconditions.union(self.schemas[current_chain[-1]].associated_observations)):
									paths.append(current_chain)
									#print "Current chain2:", current_chain, c1, c2, c3
									current_chain= [s1]; found = True; continue
						#print "@Current_chain2:", current_chain, c3
						for c4 in pathschemas[c3].child_schemas:
							found  = False
							current_chain.append(c3)
							if c4 in ends and (not c4 in current_chain):
								current_chain.append(c4);
								if not len(current_chain)> 4:
									if not self.schemas[current_chain[0]].preconditions.union(self.schemas[current_chain[0]].associated_preconditions).satisfies(self.schemas[current_chain[0]].postconditions.union(self.schemas[current_chain[-1]].associated_observations)):
										paths.append(current_chain)
										#print "Current chain3:", current_chain, c1, c2, c3, c4
										current_chain= [s1, c1]; found =  True; continue
							#print "@Current_chain3:", current_chain, c4
						if not found:
							#print "Not found 4:", current_chain
							current_chain = [s1, c1]
					if not found:
						#print "Not found 3:", current_chain
						current_chain = [s1]
				#if not found:
					#print "Not found 2:", current_chain
					#current_chain = []
			#if not found:
				#print "Not found 1:", current_chain
				#current_chain = []
		for p in paths:
			if len(p) >1 :
				self.add_chain(p)

		print "Chains found of all chains:", paths
		if len(paths) > 0:
			max_prob = 0.0; reliable = None
			for path in paths:
				prob = 0.0
				for id in path:
					s = self.get_schema_from_id(id)
					prob += s.get_probability()
					#print "S.probability::::",s.id, prob, s.postconditions.to_string()
				#print "Chain.probability::::",path, (prob+len(path))/(prob*len(path))
				if (prob+len(path))/(prob*len(path)) > max_prob:
					max_prob = float((prob+len(path))/(prob*len(path)))
					reliable = list(path)
			print "Chain found with highest reliabality:", reliable, max_prob," of all chains:", len(paths)
			return reliable
		else:
			return []


	def printf(self):
		"""Prints all the schemas in the memory"""
		for schema in self.schemas:
			print schema.to_string()


	def print_xml(self):
		"""Print XML version of memory"""
		print self.to_xml()

	def to_xml(self):
		builder = ""
		builder += "<?xml version='1.0'?>\n"
		builder += "<pschema>\n"
		for schema in self.schemas:
			builder += schema.to_xml()
		builder += "<Chains>\n"
		for c in self.chains:
			builder +=c.to_xml()
		builder += "</Chains>\n"
		builder += "<associations>\n"
		for p in self.associations.keys():
			builder += "<pair occurrences='%d'>\n"%self.associations[p]
			builder += p.first.to_xml()
			builder += p.second.to_xml()
			builder += "</pair>\n"
		builder += "</associations>\n"
		builder += "<generalised_associations>\n"
		for p in self.generalised_associations.keys():
			builder += "<pair occurrences='%d'>\n"%self.generalised_associations[p]
			builder += p.first.to_xml()
			builder += p.second.to_xml()
			builder += "</pair>\n"
		builder +="</generalised_associations>\n"
		builder +="</pschema>\n"
		return builder

	def load(self, filename):
		"""Create memory from given XML file"""
		print filename
		tree = ET.parse(filename)
		if (tree == None):
			print "Filename not found"
			return 1;
		root = tree.getroot()
		if root == None:
			#PSchema.debug(1, "Invalid XML :",filename)
			del root
			return 2
		self.parse_node(root)
		highest_id = 0
		for s in self.schemas:
			if (s.id > highest_id):
				highest_id = int(s.id)
		self.next_id = highest_id + 1
		#self.total_executions = int(self.next_id)
		del root
		return 3


	def parse_node(self, root):
		"""Create schemas from XML nodes taken from XML file"""
		has_sub_components = False
		for child in root.iter():
			if child.tag == "schema":
				#print "Loading Schema"
				self.loading_schema = Schema(self)
				for k in child.attrib.keys():
					if k =="id":
						#print "Adding schema ID: ", int(child.attrib[k])
						self.loading_schema.id = int(child.attrib[k])
					if k =="added_ID":
						#print "Adding schema ID: ", int(child.attrib[k])
						self.loading_schema.added_ID = int(child.attrib[k])
					if k =="activations":
						self.loading_schema.activations = float(child.attrib[k])
					if k =="successes":
						self.loading_schema.successes = float(child.attrib[k])
					if k =="Parent_schemas":
						#print "Adding Parent_schemas"
						d = []; z = ""; no = False
						value = child.attrib[k]
						for a1 in value:
							#print "Sub value is :", a1
							if a1 != ' ':
								z +=a1; no = True
							else:
								if no:
									#print "No is:", z
									no = int(z); z = ""
									d += [no]; no = False
						self.loading_schema.parent_schemas = list(d)

					if k =="Child_schemas":
						#print "Adding Parent_schemas"
						d = []; z = ""; no = False
						value = child.attrib[k]
						for a1 in value:
							#print "Sub value is :", a1
							if a1 != ' ':
								z +=a1; no = True
							else:
								if no:
									#print "No is:", z
									no = int(z); z = ""
									d += [no]; no = False
						#print "Loading child schema:", self.loading_schema.id, d
						self.loading_schema.child_schemas = list(d)
					if k =="Executions":
						#print "Adding Parent_schemas"
						d = []; z = ""; no = False
						value = child.attrib[k]
						for a1 in value:
							if a1 == " ":
								continue
							#print "Sub value is :", a1
							if a1 != "[" and a1 != "]" and a1 != ",":
								z +=a1; no = True; continue
							else:
								if no:
									#print "No is:",z
									no = int(z); z = ""
									d += [no]; no = False
						self.loading_schema.execution_ID = list(d)
						for l in d:
							self.total_executions +=1
				#print "Loading ID:", self.loading_schema.id
				#self.total_executions += 1
				#self.loading_schema.execution_ID = [int(self.loading_schema.id+1)]
				if len(child.attrib.keys()) > 0:
					self.schemas.append(self.loading_schema)
				else:
					self.schemas[-1].add_failed_schema(self.loading_schema)
			if child.tag == "Chains":
				for k in child.iter():
					if(k.tag == "Chain"):
						self.loading_chain = Chain()
						self.loading_chain.parse_node(k)
						self.create_chain(self.loading_chain);continue
			if (child.tag=="preconditions" or child.tag == "postconditions" or child.tag == "associated_observations" or child.tag == "disappeared_observations" or child.tag == "associated_preconditions"):
				loading_state_type = child.tag; continue
			if child.tag == "observation":
				o = self.parse_observation(child)
				#print "Ob_type:", type(o)
				o.parse_node(child)
				if o.is_generalised():
					self.loading_schema.generalised = True
				if (loading_state_type=="preconditions"):
					self.loading_schema.add_precondition(o)
				elif (loading_state_type == "associated_preconditions"):
					self.loading_schema.add_associated_preconditions(o)
				elif (loading_state_type == "postconditions"):
					self.loading_schema.add_postcondition(o)
				elif (loading_state_type == "associated_observations"):
					self.loading_schema.add_associated_observation(o)
				elif (loading_state_type == "disappeared_observations"):
					self.loading_schema.add_disappeared_observation(o)
				#if not self.loading_schema.generalised:
				self.observation_id_occurred(o.id)
				#print "Observation id occured:", o.id, self.observation_id_occurrences(o)
				self.observation_ids_seen_at(o)
				for i in range(0, int(o.activations)):
					self.observation_occurred(o)
				if self.observation_in_schemas.has_key(o.id):
					#print "Appending existing list of Id in schema:", self.observation_in_schemas[o.id].first, self.observation_in_schemas[o.id].second
					if not(self.loading_schema.id in self.observation_in_schemas[o.id].first):
						self.observation_in_schemas[o.id].second +=1.0
						self.observation_in_schemas[o.id].first.append(self.loading_schema.id)
				else:
					self.observation_in_schemas[o.id] = Pair([self.loading_schema.id], 1.0)

			if child.tag== "action":
				action = Action()
				action.parse_node(child)
				self.loading_schema.action = action
				self.emit("connect_action", action)
				has_sub_components = True
				"""elif (act =="target"):
					#print "Adding Target"
					action = TargetAction(self)
					action.parse_node(child)
					target = WorldState()
					for grand in child.iter():
						if grand.tag =="observation":
							o2 = self.parse_observation(grand)
							#print "Parsing Observation: ", type(o2)
							o2.parse_node(grand)
							#print "Target Observation: ", o2.sensor_id, o2.get_properties()
							target.add_observation(o2)
					action.target = target"""
				self.loading_schema.action = action
				loading_state_type = None
				has_sub_components = True
				continue
			if (child.tag == "associations" or child.tag == "generalised_associations"):
				has_sub_components = True
				for k in child.iter():
					if(k.tag == "pair"):
						occurrences = 0
						o1 = o2 = None
						for k1 in k.attrib.keys():
							value = k.attrib[k1]
							if (k1 == "occurrences"):
								occurrences = int(value)
						for k3 in k.iter():
							if(k3.tag == "observation"):
								if(o1 == None):
									o1 = self.parse_observation(k3)
									o1.parse_node(k3)
								else:
									o2 = self.parse_observation(k3)
									o2.parse_node(k3)

						if (o1 != None and o2 != None):
							pair = Pair(o1, o2)
							if(child.tag == "associations"):
								self.associations.set(pair, occurrences)
							elif (child.tag == "generalised_associations"):
								self.generalised_associations[pair] = occurrences

	def parse_observation(self, node):
		"""Create Observation from observation node"""
		for k in node.attrib.keys():
			#print "Observation child: ", k, node.attrib[k]
			if k =="type":
				ob = node.attrib[k]
				module = __import__(ob)
				class_ = getattr(module,ob)
				observation = class_()
		return observation

	def save( self, filename):
		"""Save memory into XML file"""
		fo = open(filename, "wb")
		fo.write(self.to_xml())
		fo.close()

	def get_total_schemas(self):
		"""Return number of total schemas in the memory"""
		return len(self.schemas)


	def set_generaliser(self, gen):
		"""Set Generaliser for the memory"""
		self.generaliser = gen


	def set_excitation_calculator(self, ec):
		"""Set Excitation calculator for the memory"""
		self.excitation_calculator = ec


	def observation_occurrences(self, o):
		"""Returns number of times given observation appeared"""
		if (self.observations.has_key(o.hash()) and self.observations[o.hash()] > 0):
			return self.observations[o.hash()]
		else:
			return 0.0


	def observation_id_occurred(self, id):
		if self.observations_ids.has_key(id):
			self.observations_ids[id] +=1.0
		else:
			self.observations_ids[id] = 1.0

	def observation_occurred_in_schemas(self, id):
		if self.observation_in_schemas.has_key(id):
			return self.observation_in_schemas[id]
		else:
			return Pair([],0.0)

	def observation_id_occurrences(self, id):
		if self.observations_ids.has_key(id):
			return self.observations_ids[id]
		else:
			return 1.0


	def observation_ids_seen_at(self, o):
		#ids = [i.id for i in ws.state]
		if self.observation_ids_seen.has_key(o.id):
			self.observation_ids_seen[o.id].append(self.total_executions)
			#print "Observation recorded previously:",o.id, self.observation_ids_seen[o.id][0], self.observation_ids_seen[o.id][-1]
		else:
			self.observation_ids_seen[o.id]= [self.total_executions]
			#print "Observation not recorded previously:",o.id, self.observation_ids_seen[o.id][0], self.observation_ids_seen[o.id][-1]
		for id in self.observation_ids_seen.keys():
			if not id==o.id:
				self.observation_ids_seen[o.id]= [self.observation_ids_seen[o.id][-1]]
				#print "Observation not seen in this session", id, self.observation_ids_seen[o.id][0], self.observation_ids_seen[o.id][-1]

	def associate_observations(self, po, ao):
		if(po.equals(ao)):
			return
		pair = Pair(po, ao)
		if (self.associations.has_key(pair) and self.associations[pair] > 0):
			self.associations[pair] = self.associations[pair] + 1
		else:
			ga_pair = self.get_generalised_association(po, ao)
			if (ga_pair != None):
				self.generalised_associations[ga_pair] = self.generalised_associations[pair] + 1
				return
			self.generaliser.assimilate_association[pair] = self.associations
			self.associations[pair] = 1


	def add_generalised_associations(self, p):
		self.generalised_associations[p] = 1


	def get_generalised_association(self, po, ao):
		for ga_pair in self.generalised_associations.keys():
			ga = ga_pair.first
			ao2 = ga_pair.second
			if(type(ga) != type(po) or not ao.equals(ao2)):
				continue
			gproperties = ga.get_properties()
			properties = po.get_properties()
			variables = {}
			for property in gproperties.keys():
				g = gproperties[property]
				if(variables.has_key(g) and variables[g] == None):
					variables[g] = properties[property]
			for v in variables.keys():
				ga.instantiate_var(v, variables[v])
			if (ga.equals(po)):
				return ga_pair
		return Pair(Observation(), Observation())

	def associated_observation_occurrences(self, po, ao):
		pair = Pair(po, ao)
		if (self.associations.has_key(pair) and self.associations[pair] > 0):
			return self.associations[pair]
		else:
			gp = self.get_generalised_association(po, ao)
			if (gp != None):
				return self.generalised_associations[pair]
			else:
				return 0

	def observation_occurred(self, o):
		if (self.observations.has_key(o.hash()) and self.observations[o.hash()] > 0):
			self.observations[o.hash()] = self.observations[o.hash()] + 1
		else:
			self.observations[o.hash()] =  1


	def get_associations(self, o):
		aslist = []
		for p in self.associations.keys():
			if(p.first.equals(o)):
				aslist.append(p.second)
		for p in self.generalised_associations.keys():
			ga = p.first
			gproperties = ga.get_properties()
			properties = o.get_concrete_properties()
			variables = {}
			for property in gproperties.keys():
				g = gproperties[property]
				if(variables.has_key(g) and variables[g] == None):
					variables[g] = properties[property]
			for v in variables.keys():
				ga.instantiate_var(v, variables[v])
			if (ga.equals(o)):
				aslist.append(p.second)
		return aslist


	def get_chains_containing(self, id):
		"""Returns chains containg given schema ID"""
		containers = [[]]
		for i in range(0, len(self.chains)):
			chain = list(self.chains[i])
			if (id in chain):
				containers.append(list(chain))
		return containers


	def record_file(self, id, ex, Agents= None):
		if Agents == None:
			with open("Excitation_record.csv", "a") as f:
				write = csv.writer(f)
				x = []
				x += [id, ex]
				write.writerow(x)
		return