import math, csv
import  statistics as stc
from Pair import Pair
from WorldState import WorldState
from Observation import Observation
from Trio import Trio
import numpy as np
class NoveltyCalculator(object):

	def __init__(self, mem):
		self.m = mem
		self.added_ids = {}
		self.ID_excitations = {}
		self.last_excitations = {}
		self.last_ws = None

	def get_excitation(self, s, ws, record = False):
		"""Calculate excitation for the schema with given WS"""
		s_post = s.postconditions.union(s.associated_observations).copy(); ignored2 = self.m.remove_ignored_preconditions(s_post)
		T = ws.satisfies(s.postconditions)
		#if s.id != 3 and s.id != 20 and s.id != 25:
		#	return 0.0
		if record:
			print "######### Calculating excitation for the schema: ", s.id, T, record, s.generalised, s.action.to_string()#, len(s.associated_observations.state)
		excitation = 1; path_length = 0; wsc = ws.copy(); self.m.remove_ignored_preconditions(wsc)
		pre = s.preconditions
		redundant = WorldState()



		if wsc.satisfies(s.preconditions.union(s.associated_preconditions)):
			path = [s.id]
			print "No need to calculate path here:", path
		else:
			path = self.calculate_path(wsc, s)

		s.set_vars_from_state(wsc)

		coords_include = len(s.action.coords.concrete_coords.keys()) >0


		excitation = 0.0; obs = Observation()
		#print "Calculating excitation for: %r"%coords_include,s.action.coords.concrete_coords.keys(), s.action.coords.concrete_coords.values(),len(s.action.coords.concrete_coords.keys()) >0, "\n", wsc.to_string()
		most_reliable = WorldState()
		observations_types = {}

		for o in wsc.state:
			if not observations_types.has_key(o.name):
				observations_types[o.name] = [o]
			else:
				observations_types[o.name].append(o)
		for k in observations_types.keys():
			if len(observations_types[k])>1:
				probability = 0.0; reliable = None
				for o in observations_types[k]:
					if float(math.e**((-1*self.m.observation_occurred_in_schemas(o.id).second)/(1.0 + self.m.observation_id_occurrences(o)))) > probability:
						probability = float(math.e**((-1*self.m.observation_occurred_in_schemas(o.id).second)/(1.0 + self.m.observation_id_occurrences(o))))
						reliable = o
				most_reliable.add_observation(reliable)
			else:
				most_reliable.add_observation(observations_types[k][0])

		excitations = []; o_len = len(wsc.state); o_ids = []
		po = s.postconditions; ao= s.associated_observations
		if s.generalised:
			while o_len > 0:
				wsc2 = WorldState(); double_found = False
				for k in observations_types.keys():
					if len(observations_types[k])<1.5:
						wsc2.add_observation(observations_types[k][0])
					for o in observations_types[k]:
						double_found  = True
						if not o.id in o_ids:
							wsc2.add_observation(o)
							o_ids.append(o.id)
							o_len -=1
							break
				if not double_found:
					o_len = 0
				#print "New Set of World state:\n", wsc2.to_string()
		for o in wsc.state:
			similarity = 0.0; last_similarity = 0.0; id_found = -1
			for o2 in po.state:
				if o.id == o2.id and s.id > id_found:
					id_found = int(s.id)
				similarity = o2.get_similarity(o, coords_include)
				if similarity > last_similarity:
					last_similarity = similarity
					obs = o2.copy()

			for o2 in ao.state:
				if o.id == o2.id and s.id > id_found:
					id_found = int(s.id)
				similarity = o2.get_similarity(o, coords_include)
				if similarity > last_similarity:
					last_similarity = similarity
					obs = o2.copy()

			#Novelty of the observation
			if self.m.observation_id_occurrences(o) > 0:
				tau1 = self.m.observation_occurred_in_schemas(o.id).second/self.m.observation_id_occurrences(o.id)
			else:
				print "O.id not occured previously:", o.id
				tau1 = 0.0
			#nov = 1 -(((4)**2)*(tau*(1-tau))**2)
			#nov = (math.e**(-1.0*tau))
			#nov = 1 - math.e**(-4*tau)
			#nov = 1 - (tau1*(1.55-tau1))**2
			nov = 1 - 4*(tau1*(1.55-1.2*tau1))**2

			if 0 > tau1 or tau1 >1:
				print "Tau value execeed the limit1:", o.id, tau1, self.m.observation_occurred_in_schemas(o.id).second,self.m.observation_id_occurrences(o.id), self.m.observation_occurred_in_schemas(o.id).first
				input("Enter to continue")

			#observation habituation
			l =[]; l1 = []; l2 = []
			l = [i for i in self.m.observation_occurred_in_schemas(o.id).first]
			for i in l:
				for j in self.m.schemas[i].execution_ID:
					if not j in l1:
						l1 += [j];
						l2.append(self.m.schemas[i].added_ID)

			if len(l1) > 2:
				#tau2 = float(max(l1))/float(self.m.total_executions)
				#tau2 = stc.mean(l)/float(self.m.total_executions)
				su = 0.0
				for i in l1[-3:]:
					su += i/float(self.m.total_executions)
				tau2 =su/3.0
			else:
				tau2 = 0.0
			#hab = (1.0 - math.e**(-3*tau2))
			#hab = (tau)**2
			#hab = 1 - math.e**(-1*tau)
			#hab = 0.018*math.e**(4*tau)
			#hab = 16*(tau*(1-tau))**2
			#hab =  4*(tau2*(1.55-1.2*tau2))**2
			#last_similarity *= 0.6
			hab = 1 - math.e**(-5*tau2)
			if 0 > tau2 or tau2 >1:
				print "Tau value execeed the limit2:", o.id, tau2, nov, hab, self.m.observation_occurred_in_schemas(o.id).first, self.m.observation_occurred_in_schemas(o.id).second
				input("Enter to continue")


			sim3 = 0.5*(nov - hab)

			ex = (0.5*last_similarity) + sim3

			if record:
				print "Observation id:%i,  last_sim: %.3f, tau1: %.3f, Nov: %.3f, tau2: %.3f, Hab:%.3f, Sim3: %.3f, Previous exci: %s, Occured in schemas: %i, occured: %i, Excitation: %.3f "%(o.id, last_similarity, tau1, nov, tau2, hab, sim3, str(excitations), self.m.observation_occurred_in_schemas(o.id).second,self.m.observation_id_occurrences(o.id), ex)

			#if record or not same_test:
			o.excitation = last_similarity
			#if o.self_flag or o.name != "visual":#Test to ignore all observations but Objects
			#	continue
			if o.id in self.added_ids.keys():
				if ex > self.added_ids[o.id].first:
					self.added_ids[o.id].first = ex
					self.last_excitations[o.id].first = ex
				if last_similarity > self.added_ids[o.id].second.first:
					self.added_ids[o.id].second.first = last_similarity
					self.last_excitations[o.id].second.first = last_similarity
				if nov > self.added_ids[o.id].second.second:
					self.added_ids[o.id].second.second = nov
					self.last_excitations[o.id].second.second = nov
				if hab > self.added_ids[o.id].second.third:
					self.added_ids[o.id].second.third = hab
					self.last_excitations[o.id].second.third = hab
			else:
				self.added_ids[o.id] = Pair(ex, Trio(last_similarity, nov, hab))
				self.last_excitations[o.id] = Pair(ex, Trio(last_similarity, nov, hab))
			self.ID_excitations[o.id] = ex
			self.last_ws = wsc.copy()
			#excitation += last_similarity
			#print "Observation excitation detected:", ex
			excitations.append(ex)


		if len(excitations) >= 2:
			excitation = (stc.mean(excitations) +stc.variance(excitations))
		else:
			excitation = excitations[0]

		sim3 =1.0; tau = 0.0; sim4 = 1.0
		if len(s.execution_ID) > 1 and self.m.total_executions:
			dif = []; excs = []; t = self.m.total_executions
			if len(s.execution_ID) >1:
				for i in range(len(s.execution_ID)-1, -1, -1):
					print "Excitation:", i,s.execution_ID[i],s.execution_ID[i]/float(t)
					e = s.execution_ID[i]/float(t)
					t -=1
					excs.append(e)
			else:
				for i in range(0, len(s.execution_ID)):
					e = s.execution_ID[i]/float(self.m.total_executions)
					excs.append(e)
			tau = float(stc.mean(excs) +stc.variance(excs))
			sim3 = math.e**(-1.1*tau)
		sim4 = (sim3*(1+s.successes))/float(1+s.activations)
		#print "Schema statics:", s.execution_ID, s.added_ID, tau, sim3, excitation, s.action.to_concrete_string()
		excitation2 =(0.6*excitation) + (abs(sim4))*0.4
		s.excitation = float(excitation2)
		if record:
			#print "Chains::::::", len(self.m.chains)
			print "\n @novelity Excitation Schema %i, added: %0.2f, executions: %s, path len: %0.2f, local_exci: %0.4f, Tau: %0.5f, S_excitation: %0.5f, Successes: %f, Activations: %f, suc/act: %.3f; fina_exci: %0.5f, Action:%s \n"%(s.id, s.added_ID, str(s.execution_ID), len(path), excitation,tau, sim3, s.successes,s.activations, sim4, s.excitation, s.action.to_concrete_string())
		return s.excitation



	def calculate_path(self, ws, s):
		"""If schema can be achieved directly then path is 1 unit long
		Else calculate chain"""
		path_length = 0; path = []
		target_state = s.postconditions.union(s.associated_observations).copy()
		path= self.m.find_path3(ws.copy(), target_state, [s.id], s.disappeared_observations, False)
		#print "@calculate_path For Schema %i path is: "%s.id, path
		return path

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

	def keep_record(self):
		for k in self.added_ids.keys():
			self.record_file(k, self.added_ids[k].first, self.added_ids[k].second.first,self.added_ids[k].second.second, self.added_ids[k].second.third)
		self.added_ids = {}

	def record_file(self, id, ex, sim, nov, hab):
		with open("Excitation_record.csv", "a") as f:
			write = csv.writer(f)
			x = []
			x += [id, ex, sim, nov, hab]
			write.writerow(x)
		return