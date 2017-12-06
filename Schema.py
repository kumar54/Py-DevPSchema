from abc import abstractmethod,ABCMeta
from gi.repository import GObject
from WorldState import WorldState
import PSchema, random
from Action import Action
from Observation import Observation
from Pair import Pair
from Trio import Trio
import inspect, math

class Schema(GObject.Object):
	#__metaclass__ = ABCMeta

	def __init__(self, mem):
		self.mem = mem
		self.preconditions = WorldState()
		self.postconditions =  WorldState()
		self.associated_observations = WorldState()
		self.associated_preconditions = WorldState()
		self.disappeared_observations = WorldState()
		self.action = Action()
		self.id  = -1
		self.generalised = False
		self.successes = 0.0
		self.excitation = 0.0
		self.activations = 0.0
		self.parent_schemas = []
		self.child_schemas = []
		self.added_ID = 0
		self.execution_ID = []
		self.failed_schemas = []


	def __lt__(self, other):
		return self.excitation < other.excitation

	def add_precondition(self, precondition):
		"""Add given observation to the Precondition"""
		self.preconditions.add_observation(precondition)

	def add_postcondition(self, postcondition):
		"""Add given observation to the Postcondition"""
		self.postconditions.add_observation(postcondition)

	def add_associated_observation(self, o):
		"""Add given observation to the associated"""
		self.associated_observations.add_observation(o)

	def add_disappeared_observation(self, o):
		"""Add given observation to the associated"""
		self.disappeared_observations.add_observation(o)

	def add_associated_preconditions(self, o):
		"""Add given observation to the associated"""
		self.associated_preconditions.add_observation(o)

	def add_failed_schema(self, s2):
		if not self.generalised:
			return
		for s in self.failed_schemas:
			if s2.equals(s):
				return
		self.failed_schemas.append(s2)

	def execute(self):
		"""Execute the schema and increment activations"""
		self.execution_ID.append(int(self.mem.total_executions))
		if (self.action != None):
			print "Executing schema action with execution ID %s Excitation = %0.4f  @execute/Schema:"%(str(self.execution_ID), self.excitation), self.action.to_concrete_string(),"\n"
			self.action.execute(); self.activations +=1; print "@Schema/execute ID: %i ,Activations: %f, Successes: %f"%(self.id, self.activations, self.successes), self.added_ID, self.execution_ID
			return 1
		else:
			self.mem.achieve_goal2(self.postconditions, [self.id], self.disappeared_observations, False)
			self.activations +=1
			return 2

	def is_post_pre(self):
		"""Retrun True if Posts and Pres are equal"""
		return self.precondition.equal(self.postcondition)


	def equals(self, so2):
		"""Returns true if two schemas are equal"""
		if (self.generalised):
			self.set_vars_from_state(so2.preconditions)
		return self.preconditions.equals(so2.preconditions) and self.associated_preconditions.equals(so2.associated_preconditions) and ( (self.action == None and so2.action == None) or (self.action != None and so2.action != None and self.action.equals(so2.action)) ) and self.postconditions.equals(so2.postconditions) and self.associated_observations.equals(so2.associated_observations) and self.disappeared_observations.equals(so2.disappeared_observations)

	def satisfies(self, pre2, a2, post2, ignore=False):
		"""Returns true is second schema is subset of first schema"""
		if (self.generalised):
			self.set_vars_from_state(pre2)
			s_post = self.postconditions.copy(); self.mem.remove_ignored_preconditions(s_post)
			c_post2 = post2.copy(); self.mem.remove_ignored_preconditions(c_post2)
			return self.preconditions.satisfies(pre2, ignore) and s_post.satisfies(c_post2)
		return self.preconditions.satisfies(pre2, ignore) and (a2 == None or (self.action != None and self.action.equals(a2))) and self.postconditions.satisfies(post2, ignore)

	def get_similarity(self, s2):
		"""Retruns similarity between two schemas
		Similarity is scalled to 1.00"""
		pre = WorldState()
		pre = s2.preconditions.copy()
		#print "@schema simi Matching with: ", s2.id,"\n",pre.to_string()
		if self.generalised:
			self.set_vars_from_state(pre)
		Total_similarity = 0.0
		similarity = self.preconditions.get_similarity(s2.preconditions)
		Total_similarity += similarity
		similarity = self.postconditions.get_similarity(s2.postconditions)
		Total_similarity += similarity
		return Total_similarity/2

	def update(self, ws):
		"""Update schema postconditions from given state"""
		found_all = True; schema_changed = False
		if self.generalised:
			wsc = ws.copy(); self.mem.remove_ignored_preconditions(wsc)
			self.set_vars_from_state(wsc)
			s_post = self.postconditions.copy(); self.mem.remove_ignored_preconditions(s_post)
			for o in s_post.state:
				found = False
				for o2 in wsc.state:
					if (o.equals(o2)):
						o.occurred(True)
						found = True
				if (not found):
					o.occurred(False)
					found_all = False
		else:
			for o in self.postconditions.state:
				found = False
				for o2 in ws.state:
					if (o.equals(o2)):
						o.occurred(True)
						found = True
				if (not found):
					print "@schem_update Observation not found:", o.to_string()
					o.occurred(False)
					found_all = False

		if(len(self.postconditions.state) == 0):
			self.successes +=1; schema_changed = True; found_all = False
			for o in ws.state:
				if not(o.self_flag):
					continue
				found = False
				for o2 in self.postconditions.state:
					if (o.equals(o2)):
						found = True; break
				if (not found):
					o.occurred(True)
					self.postconditions.add_observation(o)
		if found_all:
			self.successes +=1
			print "Schema succesful:",self.id,self.successes
		return (found_all, schema_changed)

	def copy(self):
		"""Create copy of the schema"""
		new = Schema(self.mem)
		new.preconditions= self.preconditions.copy()
		new.postconditions = self.postconditions.copy()
		new.action = self.action.copy()
		new.associated_observations = self.associated_observations.copy()
		new.disappeared_observations = self.disappeared_observations.copy()
		new.associated_preconditions = self.associated_preconditions.copy()
		new.id = int(self.id)
		if self.generalised:
			new.generalised = True
		new.activations = int(self.activations)
		new.successes = int(self.successes)
		new.excitation = float(self.excitation)
		new.parent_schemas = list(self.parent_schemas)
		new.child_schemas = list(self.child_schemas)
		new.execution_ID = list(self.execution_ID)
		new.failed_schemas = list(self.failed_schemas)
		new.added_ID =  self.added_ID
		return new


	def is_synthetic(self):
		for o in self.preconditions.state:
			if (type(o).__name___ == "SyntheticObservation"):
				return True
		return False

	def get_probability(self):
		"""Return probability of the schema
		Successful schemas are more reliable"""
		total = 0.0; num = 0.0
		predictions = self.postconditions.get_predictions()
		for o in predictions.state:
			total += o.get_probability()
			num +=1.0
		if (num == 0.0):
			return 1.0
		return (total/num)

	def is_generalised(self):
		"""Return True iof schema is generalised"""
		Gen = False
		for o in self.preconditions.state:
			Gen = o.is_generalised()
			if Gen:
				return True
		return False

	def to_string(self):
		"""Return schema as string for print"""
		builder =""
		builder += "\nSchema %d: Added at: %d Executed  at: %s\n"%(self.id, self.added_ID, str(self.execution_ID))
		builder =="=======\n"
		builder +="Activated: %0.2f times, Success: %0.2f times, Parent_schemas: %s, Child_schemas: %s\n"%(float(self.activations), float(self.successes),str(self.parent_schemas), str(self.child_schemas))

		builder +="\nPre-Conditions:\n"

		builder += self.preconditions.to_string()

		builder +="\nAssociated Pre-Conditions:\n"

		builder += self.associated_preconditions.to_string()

		builder += "\nAction:\n"
		if (self.action != None):
			builder +=self.action.to_string()
		else:
			builder += "No action assigned.\n"

		builder +="\nPost-Conditions:\n"
		builder +=self.postconditions.to_string()

		builder +="\nAssociated Observations:\n"
		builder += self.associated_observations.to_string()

		builder +="\nDisappeared Observations:\n"
		builder += self.disappeared_observations.to_string()

		builder += "\n"
		return builder



	def to_concrete_string(self):
		"""Return schema as string for print"""
		if not self.generalised:
			print "Schema not generalised to present concrete state"
			return
		builder =""
		builder += "\nSchema %d: Added at: %d\n"%(self.id, self.added_ID)
		builder =="=======\n"

		builder +="Activated: %0.2f times, Success: %0.2f times, Parent_schemas: %s, Child_schemas: %s\n"%(float(self.activations), float(self.successes),str(self.parent_schemas), str(self.child_schemas))

		builder +="\nPre-Conditions:\n"

		builder += self.preconditions.to_concrete_string()

		builder +="\nAssociated Pre-Conditions:\n"

		builder += self.associated_preconditions.to_concrete_string()

		builder += "\nAction:\n"
		if (self.action != None):
			builder +=self.action.to_concrete_string()
		else:
			builder += "No action assigned.\n"

		builder +="\nPost-Conditions:\n"
		builder +=self.postconditions.to_concrete_string()

		builder +="\nAssociated Observations:\n"
		builder += self.associated_observations.to_concrete_string()

		builder +="\nDisappeared Observations:\n"
		builder += self.disappeared_observations.to_concrete_string()

		builder += "\n"
		return builder

	def to_xml(self):
		"""Return schema in XML format"""
		c = " "; d = " "
		for a in self.parent_schemas:
			c +="%s "%str(a)
		for b in self.child_schemas:
			d +="%s "%str(b)
		builder = ""
		builder += "<schema id='%d' added_ID= '%d' activations='%f' successes = '%f' Parent_schemas =  '%s' Child_schemas = '%s'  Executions = '%s' >\n"%(self.id, self.added_ID, self.activations, self.successes, c, d, str(self.execution_ID))
		builder += "<preconditions>\n"
		builder += self.preconditions.to_xml()
		builder += "</preconditions>\n"
		builder += "<associated_preconditions>\n"
		builder += self.associated_preconditions.to_xml()
		builder += "</associated_preconditions>\n"
		if(self.action != None):
			builder += self.action.to_xml()
		builder += "<postconditions>\n"
		builder += self.postconditions.to_xml()
		builder += "</postconditions>\n"
		builder += "<associated_observations>\n"
		builder += self.associated_observations.to_xml()
		builder += "</associated_observations>\n"
		builder += "<disappeared_observations>\n"
		builder += self.disappeared_observations.to_xml()
		builder += "</disappeared_observations>\n"
		builder += "</schema>\n"
		#print "Schema added:", self.id
		"""if self.generalised and len(self.failed_schemas) >0:
			for s in self.failed_schemas:
				c = " "; d = " "
				for a in self.parent_schemas:
					c +="%s "%str(a)
				for b in self.child_schemas:
					d +="%s "%str(b)
				builder += "<schema >\n"
				builder += "<preconditions>\n"
				builder += s.preconditions.to_xml()
				builder += "</preconditions>\n"
				builder += "<associated_preconditions>\n"
				builder += s.associated_preconditions.to_xml()
				builder += "</associated_preconditions>\n"
				if(s.action != None):
					builder += s.action.to_xml()
				builder += "<postconditions>\n"
				builder += s.postconditions.to_xml()
				builder += "</postconditions>\n"
				builder += "<associated_observations>\n"
				builder += s.associated_observations.to_xml()
				builder += "</associated_observations>\n"
				builder += "<disappeared_observations>\n"
				builder += s.disappeared_observations.to_xml()
				builder += "</disappeared_observations>\n"
				builder += "</schema>\n"""""
				#print "Added failed schema"
		return builder

	def set_vars_from_state(self, concrete):
		"""Set variables of generalised schema from given concrete state"""
		#print "\nInstiating Instantiate:::",inspect.stack()[1][3]
		concrete_ws = concrete.copy()
		self.mem.remove_ignored_preconditions(concrete_ws)
		redundant = WorldState(); variables = {}
		#print "@set_var_state for generalised schema:", self.id, self.generalised
		#print "@Set_var_called:",self.generalised, len(concrete_ws.state)> 0,inspect.stack()[1][3]
		if (not self.generalised) or len(concrete_ws.state)== 0:
			return
		observations_types = {}
		for o in concrete_ws.state:
			if not observations_types.has_key(o.name):
				observations_types[o.name] = [o]
			else:
				observations_types[o.name].append(o)
		most_reliable = WorldState()
		for k in observations_types.keys():
			if len(observations_types[k])>1:
				probability = -1.0; reliable = None
				"""for o in observations_types[k]:
					if float(o.get_probability())/(1+self.mem.observation_id_occurrences(o)) > probability:
						probability = float(o.get_probability())/self.mem.observation_id_occurrences(o)
						reliable = o.copy()
					elif len(o.get_properties().keys()) > len(reliable.get_properties().keys()) or len(o.coords.get_coords().keys()) > len(reliable.coords.get_coords().keys()):
						reliable = o.copy()
						probability = float(o.get_probability())/self.mem.observation_id_occurrences(o)"""
				for o in observations_types[k]:
					if self.mem.observation_id_occurrences(o) > 0:
						tau1 = self.mem.observation_occurred_in_schemas(o.id).second/self.mem.observation_id_occurrences(o.id)
					else:
						tau1 = 0.0
					nov = 1 - 4*(tau1*(1.55-1.2*tau1))**2

					if 0 > tau1 or tau1 >1.0:
						print "Tau value execeed the limit1@set_var_state:", o.id, tau1, self.mem.observation_occurred_in_schemas(o.id).second,self.mem.observation_id_occurrences(o), self.mem.observation_occurred_in_schemas(o.id).first
						input("Enter to continue")
					#observation habituation
					l =[]; l1 = []; l2 = []
					l = [i for i in self.mem.observation_occurred_in_schemas(o.id).first]
					for i in l: l1 += self.mem.schemas[i].execution_ID; l2.append(self.mem.schemas[i].added_ID)
					if len(l1) > 0:
						tau2 = float(max(l1))/float(self.mem.total_executions)
						su = 0.0
						for i in l1:
							su += i/float(self.mem.total_executions)
						tau2 =su/len(l1)
					else:
						tau2 = 0.0
					hab = 1 - math.e**(-5*tau2)
					#hab =  4*(tau2*(1.55-1.2*tau2))**2
					#hab = 1 - math.e**(-3*tau2)
					if 0 > tau2 or tau2 >1.0:
						print "Tau value execeed the limit2@set_var_state:", o.id,tau2, nov, hab, self.mem.observation_occurred_in_schemas(o.id).first, self.mem.observation_occurred_in_schemas(o.id).second
						input("Enter to continue")
					sim3 = (nov - hab)
					print "Observation at Set_var:", o.id, nov, hab,sim3, l1
					if sim3 > probability:
						reliable = o
						probability = sim3
				if reliable !=None:
					most_reliable.add_observation(reliable)
			else:
				most_reliable.add_observation(observations_types[k][0])
		print "Worldstate found to reliable for instantiation:",inspect.stack()[1][3],"\n", most_reliable.to_string()

		post_props = {}
		post = self.postconditions.union(self.associated_observations)
		for o in post.state:
			#print "@set_var Props Before: ", o.props, o.get_properties()
			ps = o.get_properties()
			for p in ps.keys():
				if not(post_props.has_key(p)):
					post_props[p] = ps[p]
			for c in o.coords.variable_coords.keys():
				if not(post_props.has_key(c)):
					post_props[c] = o.coords.variable_coords[c]
		#print "All generalised prosp found:", post_props

		concrete_props = {}
		for o in most_reliable.state:
			ps = o.get_concrete_properties()
			for p in ps.keys():
				if not(concrete_props.has_key(p)):
					concrete_props[p] = ps[p]
			for c in o.coords.concrete_coords.keys():
				if not(concrete_props.has_key(c)):
					concrete_props[c] = o.coords.concrete_coords[c]
		#print "All concrete prosp found:", concrete_props

		for p in concrete_props.keys():
			if post_props.has_key(p) and "$" in str(post_props[p]):
				P = Pair(post_props[p],concrete_props[p])
				if not variables.has_key(p):
					variables[p]= P

		for k in variables.keys():
			#print "Variable to be changed:", k, str(variables[k])
			if "$" in str(variables[k].second):
				return

		for o in self.preconditions.state:
			#print "\n@set_var Props in preconditions Before: ", o.get_properties()
			ps = o.get_properties()
			for p in ps.keys():
				if variables.has_key(p):
					#if variables[p].first == ps[p]:
					#print "Sending for instatntiating:", p, variables[p].second
					o.instantiate_var(p, variables[p].second)
			cs = o.coords.get_coords()
			for c in cs.keys():
				#print "Coords in variable:",c, variables[c].second, variables[c].first, cs[c]
				if variables.has_key(c):
					if variables[c].first == cs[c]:
						o.instantiate_var(c, variables[c].second)
			#print "@set_var Props in preconditions After : ", o.props, o.coords.concrete_coords, o.get_properties(),o.coords.get_coords(),"\n"

		for o in self.associated_preconditions.state:
			#print "\n@set_var Props in associtaed preconditions Before: ", o.get_properties()
			ps = o.get_properties()
			for p in ps.keys():
				if variables.has_key(p):
					#if variables[p].first == ps[p]:
					#print "Sending for instatntiating:", p, variables[p].second
					o.instantiate_var(p, variables[p].second)
			cs = o.coords.get_coords()
			for c in cs.keys():
				#print "Coords in variable:",c, variables[c].second, variables[c].first, cs[c]
				if variables.has_key(c):
					if variables[c].first == cs[c]:
						o.instantiate_var(c, variables[c].second)
			#print "@set_var Props in associated preconditions After : ", o.props, o.coords.concrete_coords, o.get_properties(),o.coords.get_coords(),"\n"

		for o in self.postconditions.state:
			#print "\n@set_var Props in postconditions Before: ", o.get_properties(), o.coords.get_coords(), o.id
			ps = o.get_properties()
			for p in ps.keys():
				if variables.has_key(p):
					#if variables[p].first == ps[p]:
					o.instantiate_var(p, variables[p].second)
			cs = o.coords.get_coords()
			for c in cs.keys():
				#print "Coords in variable:",c, variables[c].second, variables[c].first, cs[c]
				if variables.has_key(c):
					#print "Instantiating:", cs[c], variables[c].first, cs[c]== variables[c].first, variables[c].second
					#if variables[c].first == cs[c]:
					o.instantiate_var(c, variables[c].second)
			#print "@set_var Props in postconditions after : ", o.props, o.coords.concrete_coords,"\n"

		for o in self.associated_observations.state:
			#print "\n@set_var Props in associated_observations Before: ", o.get_properties(), o.coords.get_coords(), o.id
			ps = o.get_properties()
			for p in ps.keys():
				if variables.has_key(p):
					#if variables[p].first == ps[p]:
					o.instantiate_var(p, variables[p].second)
			cs = o.coords.get_coords()
			for c in cs.keys():
				#print "Coords in variable:",c, variables[c].second, variables[c].first, cs[c]
				if variables.has_key(c):
					#print "Instantiating:", cs[c], variables[c].first, cs[c]== variables[c].first, variables[c].second
					#if variables[c].first == cs[c]:
					o.instantiate_var(c, variables[c].second)
			#print "@set_var Props in associated_observations after : ", o.props, o.coords.concrete_coords,"\n"
		for o in self.disappeared_observations.state:
			#print "\n@set_var Props in associated_observations Before: ", o.get_properties(), o.coords.get_coords(), o.id
			ps = o.get_properties()
			for p in ps.keys():
				if variables.has_key(p):
					#if variables[p].first == ps[p]:
					o.instantiate_var(p, variables[p].second)
			cs = o.coords.get_coords()
			for c in cs.keys():
				#print "Coords in variable:",c, variables[c].second, variables[c].first, cs[c]
				if variables.has_key(c):
					#print "Instantiating:", cs[c], variables[c].first, cs[c]== variables[c].first, variables[c].second
					#if variables[c].first == cs[c]:
					o.instantiate_var(c, variables[c].second)

		props = self.action.get_properties(); props.update(self.action.coords.get_coords())
		#print "Action props:", props
		if len(props) > 0:
			for p in props.keys():
				if variables.has_key(p):# and variables[p].first == props[p]:
					#print "Action instantiated:", p, variables[p].first, variables[p].second
					self.action.instantiate_var(p, variables[p].second)
		#print "@set_vars Action props:",self.action.props, self.action.coords.concrete_coords

		#print "\n@@@@@@@@@@Finished All Instantiating@@@@@@@:", self.action.to_concrete_string()
		return

GObject.type_register(Schema)