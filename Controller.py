#!/usr/bin/env python
#!/usr/local/bin python3
from gi.repository import Gtk, GObject
import PSchema, os
from WorldState import WorldState
from Observation import Observation
from Action import Action
import yarp, time, socket, select, threading, random, csv, datetime
import numpy as np
#from pympler.tracker import SummaryTracker


class Controller(GObject.Object):

	__gsignals__ = {
			 "executeChain" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ())
	}

	HAND_ID = 1   #Changed ID from 1 to 2

	def __init__(self):
		GObject.Object.__init__(self)
		# Setup the GUI
		self.builder = Gtk.Builder()
		self.builder.add_from_file("Controller.ui")
		self.win = self.builder.get_object("winMain")
		self.requestWin = self.builder.get_object("winRequest")
		self.output = self.builder.get_object("txtOutput").get_buffer()
		self.requestTxt = self.builder.get_object("txtRequestWorldState").get_buffer()
		self.showBtn = self.builder.get_object("btnShowPlan")
		self.executeBtn = self.builder.get_object("btnExecute")
		self.totalSchemas = self.builder.get_object("lblTotalSchemas")

		#self.connect("delete_event", self.quit)
		#self.connect("destroy", self.quit)

		self.lastState = None
		self.last_ws = None
		self.ws = None
		self.excited_agent = None
		self.observing = None
		self.path = None
		self.executions = 0
		self.observations = []; self.id = 1
		#self. tracker = SummaryTracker()

		signals = {
				"on_win_destroyed" : self.quit,
				"on_quit_clicked" : self.quit,
				"on_bootstrap_clicked" : self.bootstrap,
				"on_play_toggled" : self.play,
				"on_step_clicked" : self.step,
				"on_clean_clicked" : self.clean,
				"on_save_clicked" : self.save,
				"on_open_clicked" : self.load,
				"on_excitation_clicked" : self.excitation,
				"on_request_clicked" : self.show_request,
				"on_clear_clicked" : self.clear,
				"on_show_plan_clicked": self.show_plan,
				"on_execute_clicked" : self.execute,
				"on_step_plan_clicked" : self.step_plan,
				"on_add_clicked" : self.add,
		}
		self.builder.connect_signals(signals)

		self.d =  str(datetime.datetime.now().date())
		self.d += str(datetime.datetime.now().time())

		self.s_d = "./Results/Schemas_record_%s.csv"%self.d
		self.ss_d = "./Results/Schemas_%s.xml"%self.d
		self.c_d ="./Results/Chains_record_%s.csv"%self.d


		schemas_record = open(self.s_d, "w")
		chains_record = open(self.c_d, "w")
		schemas = open(self.ss_d, "w")




		# Display our window
		self.win.show_all()

		# Connect to SMC
		yarp.Network.init()
		self.portactsender = yarp.Port()
		self.portactreceiver = yarp.BufferedPortBottle()
		self.portactstatusreceiver = yarp.BufferedPortBottle()
		self.portstatereceiver = yarp.BufferedPortBottle()


		self.portactsender.open("/PSchema/ActionsCommand:o")
		self.portactreceiver.open("/PSchema/ActionsAvailable:i")
		self.portactstatusreceiver.open("/PSchema/ActionsStatus:i")
		self.portstatereceiver.open("/PSchema/Sensors:i")



		yarp.Network.connect("/sandbox/Sensors:o", "/PSchema/Sensors:i")
		yarp.Network.connect("/sandbox/ActionAvailable:o", "/PSchema/ActionsAvailable:i")
		yarp.Network.connect("/sandbox/ActionStatus:o", "/PSchema/ActionsStatus:i")
		yarp.Network.connect("/PSchema/ActionsCommand:o","/sandbox/ActionsCommand:i")

		self.playing = False
		self.total = 0
		self.last_no = 0
		self.attempt =  1
		self.action_status = None
		self.boots_mode = True; self.play_mode = False

		self.excitedState = None
		self.current_excited_agents = None
		self.current_excitation = None
		self.current_executed_schema = None
		self.current_action = None
		self.received_message = None

		self.current_excitedState = None

		# Create our schema memory
		self.memory = PSchema.Memory()
		#self.memory = Pschema()

		self.requestState = WorldState()


		# Use our custom excitation calculator based on saliency
		# information provided by the lower level short-term memory
		#sal_calc = SaliencyCalculator(self.memory)
		#self.memory.set_excitation_calculator(sal_calc)

		self.memory.connect("connect_action", self.connect_action)
		self.memory.connect("update_state", self.update_state)
		self.connect("executeChain", self.execute)


		#Setup RPC server  **********It seems there is no function of this here
		GObject.threads_init()
		self.running = True
		#self.rpcPort = yarp.Port()
		#self.rpcPort.open("/schema/rpc")
		#thread = threading.Thread(target=self.checkRPC)
		thread = threading.Thread(target=self.connected)
		#thread.start()

		# Start the GTK main loop
		#Gtk.main()


	def save(self, caller=None):
		self.memory.save(self.ss_d)
		"""buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
		chooser = Gtk.FileChooserDialog("Save schema memory",
										self.win,
										Gtk.FileChooserAction.SAVE,
										buttons)
		chooser.set_do_overwrite_confirmation(True)
		chooser.set_default_response(Gtk.ResponseType.OK)
		chooser.set_current_name("schemasxx.xml")
		response = chooser.run()
		if response == Gtk.ResponseType.OK:
			saveFilename = chooser.get_filename()
			self.memory.save(saveFilename)
			chooser.destroy()
		else:
			chooser.destroy()"""


	def load(self, caller=None):
		buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
		chooser = Gtk.FileChooserDialog("Load a schema memory",
				self.win,
				Gtk.FileChooserAction.OPEN,
				buttons)

		chooser.set_default_response(Gtk.ResponseType.OK)

		allfilter = Gtk.FileFilter()
		allfilter.set_name("All Files")
		allfilter.add_pattern("*")

		schemafilter = Gtk.FileFilter()
		schemafilter.set_name("Schema XML Files (*.xml)")
		schemafilter.add_pattern("*.xml")

		chooser.add_filter(schemafilter)
		chooser.add_filter(allfilter)

		response = chooser.run()

		if response == Gtk.ResponseType.OK:
			loadFilename = chooser.get_filename()
			#self.memory.connect("connect_action", self.connect_action)
			print self.memory.load(loadFilename)
			self.update_total_schemas()
			chooser.destroy()
		else:
			chooser.destroy()

		for s in self.memory.schemas:
			for o in s.postconditions.union(s.associated_observations.union(s.disappeared_observations)).state:
				found  = False
				for o2 in self.observations:
					#print "Obs:", o.to_string(), o2.to_string()
					if o.similar(o2, False):
						found = True; break
				if not found:
					if self.id <= o.id:
						self.id = o.id + 1
					#print "Adding obs:", self.id, o.id, o.to_string()
					self.observations.append(o)
		for id in self.memory.observation_in_schemas.keys():
			print "Observation:%i, Seen in schemas: %s, seen times: %f, total occurences: %f"%(id, str(self.memory.observation_in_schemas[id].first), self.memory.observation_in_schemas[id].second, self.memory.observation_id_occurrences(id))
		print "Total Executions:", self.memory.total_executions


	def clean(self, caller = None):
		print "Current Schema/State Cleaned"
		self.memory.current_schema = None

	def connect_action(self, caller, action):
		#print "@connect_action Action:", type(action), action.props
		action.connect("abstract_signal", self.abstract_action)
		#print "All Done"

	def set_value(self, val):
		value = None
		try:
			value = float(val)
		except:
			try:
				value = int(val)
			except:
				value = str(val)
		return value



	def connected(self):
		print "Getting Message over Yarp"
		response = yarp.Bottle()
		self.portreceiver.read(response)
		print "Response recieved:", response.toString()
		self.received_message = (response.toString()).split()
		if self.received_message[0] == "sensors":
			ws= self.construct_worldstate(response)
			if self.ws != None:
				self.lastState = self.ws.copy()
			self.ws = ws
			print "WS:\n",self.ws.to_string()

		elif self.received_message[0] == "action_status":
			self.action_status_check(response)

		elif self.received_message[0] == "bootstrap":
			self.bootstrap1()

		else:
			print "Invalid response received:", response


	def check_bootstrap(self, wait=False):
		response = yarp.Bottle()
		response = self.portactreceiver.read(wait)

		if response != None:
			print "Response:\n", response.toString()
			self.build_action(response)
		return

	def build_action(self, response):
		i = 0; A = None
		while i <response.size():
			if response.get(i).asString() == "Action":
				if A != None:
					A.connect("abstract_signal", self.abstract_action)
					self.bootstrap_action(A); A = None
				A =  Action()
				A.name = response.get(i+1).asString()
				i +=2; continue
			else:
				p = response.get(i).asString()
				try:
					ps = response.get(i+1).asDouble()
				except:
					try:
						ps = response.get(i+1).asInt()
					except:
						ps = response.get(i+1).asString()

				if type(ps)==type(str()) and ps[0] == "$":
					A.props_var[p] = response.get(i+1).asString()
					A.props[p] = None
				else:
					A.props[p] = ps; A.props_var[p] = None
				i +=2; continue
		A.connect("abstract_signal", self.abstract_action)
		self.bootstrap_action(A)

	def bootstrap(self, caller=None):
		"""Perform all basic reaches and other actions
		(grasps, presses, observes, etc.) to provide the
		schema memory with the lowest level set of actions."""
		#status = self.memory.update_world_state(self.get_sensors())
		print "Bootstrap Update state"
		for y in range(0,7):#7
			for x in range(0, 9):#9
				if (x>1 and x<7 and y>0 and y<6):
					reach = Action()
					reach.name = "reach"
					reach.props["x"] = float(x)
					reach.props["y"] = float(y)
					reach.connect("abstract_signal", self.abstract_action)
					self.bootstrap_action(reach)
				saccade = Action()
				saccade.name = "saccade"
				saccade.props["x"] = float(x)
				saccade.props["y"] = float(y)
				#saccade.connect("abstract_signal", self.abstract_action)
				#self.bootstrap_action(saccade)
		grasp = Action()
		grasp.name = "grasp"
		grasp.connect("abstract_signal", self.abstract_action)
		#self.bootstrap_action(grasp)
		release = Action()
		release.name = "release"
		release.connect("abstract_signal", self.abstract_action)
		#self.bootstrap_action(release)
		press = Action()
		press.name = "press"
		press.connect("abstract_signal", self.abstract_action)
		#self.bootstrap_action(press)


	def bootstrap_action(self, action):
		"""Perform an action as part of the bootstrapping
		phase if it's not already in the schema memory."""
		#ws = self.get_sensors()
		#self.memory.update_world_state(ws)
		#self.memory.ws = None
		if not self.memory.get_schema_from_action(action):
			print "****************************************************\n"
			print "Action from schema",self.memory.get_schema_from_action(action),"\n",action.to_string()
			#status = self.memory.update_world_state(self.get_sensors())
			#print "Updated state: ",status
			Gtk.main_iteration_do(False)
			ws1 = self.get_sensors()
			print "Taking Action"
			#self.memory.update_world_state(ws)#New system
			self.memory.take_action(action)
			Gtk.main_iteration_do(False)
			#self.record_file()
			self.current_action = None
			self.current_executed_schema = self.memory.current_schema
			ws2 = self.get_sensors()
			#ws = ws1.complement(ws2)
			status = self.memory.update_world_state(ws2)
			#self.set_home()
			print "Update state 2 : ",status
			Gtk.main_iteration_do(False)
		else:
			print "Action already exists"

		print "Total : %i\n"%self.memory.get_total_schemas()
		self.update_total_schemas()

	def excitation(self, caller=None, ws=None):
		"""Find the schema most excited by the
		current world state and display it in
		the UI."""
		if ws ==None:
			ws = self.get_sensors()
		else:
			record = False
		#self.excitedState = ws.copy()

		if self.memory.ws == None:
			print "WS not exists; adding new state to calculate excitation"
			self.memory.update_world_state(ws)
			self.excited_agent = self.memory.get_excited_agent(ws, True)
			self.excitedState = ws
		else:
			if self.excitedState !=None:
				if not self.excitedState.equals(ws):
					print "State changed after last excitation calculation"
					self.memory.update_world_state(ws)
					self.excited_agent = self.memory.get_excited_agent(ws, True)
					self.excitedState = ws
				else:
					print"Excitation already calculated for the state"
					return
			else:
				self.excited_agent = self.memory.get_excited_agent(ws, True)
				self.excitedState = ws

		#self.memory.excitation_calculator.keep_record()

		message = ""
		if str(type(self.excited_agent[0].first)) == "<class 'Chain.Chain'>":
			print "Excited_agent@Controller.excitation: Excited chain is:",self.excited_agent[0].first.sequence, self.excited_agent[0].second
			message += "Currently most excited agent is a chain: %s, Excitation: %s, Successes:  %i, Activations: %i, total executions: %i"%(str(self.excited_agent[0].first.sequence), str(self.excited_agent[0].second),self.excited_agent[0].first.successes,self.excited_agent[0].first.activations, self.memory.total_executions)
			for i in self.excited_agent[0].first.sequence:
				s = self.memory.get_schema_from_id(i)
				message +="\n %s\n"%s.to_string()
			message += "\nI currently see:\n\n"
			message += "%s\n" %ws.to_string()

		else:
			print "Excited_agent@Controller.excitation:Schema ID ", self.excited_agent[0].first.id, self.excited_agent[0].second, len(self.excited_agent), self.excited_agent[0].first.action.to_concrete_string()
			if len(self.excited_agent) == 0:
				message += "\nI don't currently have any schemas to be excited by this."
			else:
				message += "\nThe most excited schema with excitation %f is:\n\n%s"%(self.excited_agent[0].second, self.excited_agent[0].first.to_string())
			message += "\nI currently see:\n\n"
			for o in ws.state:
				count = 0
				for o2 in self.excited_agent[0].first.postconditions.state:
					if o.get_similarity(o2) > 0.5:
						count+=1
						break
				message += "%s -- This reminds me considerably of %d schemas\n" % (o.to_string(), count)

			message += "\nTotal observations & executions still recorded: '%i', %i "%(len(self.observations),self.memory.total_executions)
		self.output.set_text(message)



	def play(self, caller=None):
		"""Continue executing the most excited schema until told to stop by the user."""
		self.playing = not self.playing
		if self.playing:
			GObject.idle_add(self.step)

	def step(self, caller=None):
		"""Execute the most excited schema and then
		stop."""
		#self.bootstrap_check()

		print("\n=============================================")
		print ("Step function\n=============================================\n")
		if len(self.memory.schemas) == 0:
			self.check_bootstrap(True)

		self.excitation()
		#print "Most excited agent is:", self.excited_agent[0].first.id, self.excited_agent[0].second
		#print "Chains:::::::::::1::", len(self.memory.chains)
		if self.excited_agent == None:
			print "Execution with none:", self.memory.ws.to_string()
			Agents = self.memory.execute_excited_agent(None, None, False)
		else:
			print "Execution with:", self.excited_agent[0].first, self.excitedState.to_string()
			self.memory.execute_excited_agent(self.excitedState, self.excited_agent, False)

		self.memory.excitation_calculator.keep_record()
		#print "Chains:::::::::::2::", len(self.memory.chains)
		self.record_file()
		ws = self.get_sensors()
		status = self.memory.update_world_state(ws)
		print "@Step status 3 updated with code ",status," and state:\n",self.memory.ws.to_string()
		self.save()

		self.excitedState = None
		self.excitation(None, ws)
		#self.check_bootstrap()
		print "updating total schemas %i, & chains %i, Total_excitations: %i"%(self.memory.get_total_schemas(), len(self.memory.chains), self.memory.total_executions)
		self.update_total_schemas()
		#self.memory.load("schemasxx.xml")
		if self.playing:
			GObject.idle_add(self.step)



	def record_file(self, Agents= None):
		if Agents == None:
			with open(self.s_d, "a") as f:
				write = csv.writer(f)
				x = []
				for s in self.memory.schemas:
					if len(s.execution_ID) < 1:
						continue
					x += [s.id, s.excitation]
				write.writerow(x)
			with open(self.c_d, "a") as f:
				write = csv.writer(f)
				x = []
				#print "Chains In memory:", len(self.memory.chains)
				for c in self.memory.chains:
					#print "Chains record:",c.sequence, c.excitation
					x += [c.sequence, c.excitation]
				write.writerow(x)
			return


	def update_state(self, caller):
		ws = self.get_sensors()
		#print "Updating state: \n", ws.to_string()
		self.excitedState = ws
		r = self.memory.update_world_state(ws)
		print "@update_state status 1 updated with code:",r," and state:\n",self.memory.ws.to_string()


	def abstract_action(self, caller, A): #*args)
		#print "@abstract_action :", A.name, A.props, A.coords.concrete_coords
		query = yarp.Bottle()
		response = yarp.Bottle()
		query.addString(A.name)
		for a in A.props.keys():
			query.addString(a)
			if type(A.props[a]) == type(str()):
				query.addString(A.props[a])
			elif type(A.props[a]) == type(int()):
				query.addInt(A.props[a])
			elif type(A.props[a]) == type(float()):
				query.addDouble(A.props[a])
		for c in A.coords.concrete_coords.keys():
			query.addString(c)
			if type(A.coords.concrete_coords[c]) == type(str()):
				query.addString(A.coords.concrete_coords[c])
			elif type(A.coords.concrete_coords[c]) == type(int()):
				query.addInt(A.coords.concrete_coords[c])
			elif type(A.coords.concrete_coords[c]) == type(float()):
				query.addDouble(A.coords.concrete_coords[c])
		print "\nSending query:\n", query.toString()
		self.portactsender.write(query)
		print "Query sent, waiting for response:", datetime.datetime.now()
		response = self.portactstatusreceiver.read(True)
		self.action_status_check(response.toString())
		return


	def action_status_check(self, response):
		self.action_status = str(response)
		if self.action_status == "In_Progress":
			print "@Controller action_status_check In progress and attempts:",self.attempt
			self.in_progress()
		elif self.action_status == "Failed":
			print "@action_status_check Action Failed & attempts:",self.attempt, self.current_executed_schema.action.to_string()
			if self.attempt <4 and self.action_status == "Failed":
				self.attempt +=1
				self.abstract_action(self, self.current_executed_schema.action)
			if self.attempt >=4:
				self.action_status = "SUCCESS"
				self.action_status_check(self.action_status)
		elif self.action_status == "SUCCESS":
			print "@action_status_check Action completed successfully with attempts:", self.attempt
			if self.attempt == 4:
				self.memory.current_schema.activations += 1.0; self.attempt = 1
			if 1 < self.attempt < 4:
				self.memory.current_schema.activations += 0.5; self.attempt = 1
		else:
			print "@action_status_check Invalid response received:\n", response
		return

	def in_progress(self):
		print "@in_progress Gettign WS"
		ws = self.get_sensors()
		wsc = ws.copy(); #self.memory.remove_ignored_preconditions(wsc)
		new_change = self.excitedState.complement(wsc)
		if len(new_change.state) == 0:
			new_change = wsc.complement(self.excitedState)
		if len(new_change.state) > 0:
			print "@in_progress Getting excitation for new WS:\n",new_change.to_string()
			agent = self.memory.get_excited_agent(new_change)
			if agent[0].second > self.current_excitation:
				print "@in_progress New state is more excited, executing it"
				self.excitedState = ws; self.memory.current_schema = None; self.memory.current_chain = None
				self.memory.ws = ws
				self.memory.execute_excited_agent(self.excitedState)
				print "Current Schema with new excitation is:",self.memory.current_schema.id
			else:
				print "@in_progress Last schema is still most excited"
				query = yarp.Bottle()
				query.addString("proceed")
				self.portactsender.write(query)
				response = yarp.Bottle()
				response = self.portactstatusreceiver.read(True)
				self.action_status_check(response.toString())
		else:
			print "@in_progress No significant change detected; Proceed with last action"
			query = yarp.Bottle()
			query.addString("proceed")
			self.portactsender.write(query)
			response = yarp.Bottle()
			response = self.portactstatusreceiver.read(True)
			self.action_status_check(response.toString())
		return


	def set_home(self):
		"""Sets manipulator to Home"""
		query = yarp.Bottle()
		response = yarp.Bottle()
		query.clear()
		response.clear()
		query.addString("home")
		#print("sending get_sensors")
		self.portactsender.write(query)
		return


	def get_sensors(self):
		"""Retrieve sensor information from the
		RPC controller and then build a world state
		based upon it."""
		query = yarp.Bottle()
		response = yarp.Bottle()
		query.clear()
		query.addString("sensors")
		self.portactsender.write(query)
		response.clear()
		print "Request sent for WS"
		response = self.portstatereceiver.read(True)
		print "State recceived:\n", response.toString()
		worldstate = self.construct_worldstate((response.toString()).split())
		self.lastState = worldstate.copy()
		print ("world state created")
		return worldstate



	def construct_worldstate(self, response):
		"""Construct a world state based upon WS request"""
		i = 0;
		worldstate = WorldState()
		visual_observations = []
		holding_object = None; O = Observation()
		#print "Check response:", response,response[1]
		for i in range(len(response)):
			if response[i] == "observation":
				O = Observation()
				b = i+1
				while (b <len(response)):
					if response[b] == "observation":
						if O.name =="visual":
							if O.props['colour'] !="hand":
								self.add_observation(worldstate, O)
						else:
							self.add_observation(worldstate, O)
						break
					elif response[b] == "name":
						#print "Name:", response[b+1]
						O.name = response[b+1]; b = b+2
					elif response[b] == "Self_flag":
						#print "Self_flag:", response[b+1]
						if int(response[b+1]) == 1:
							O.self_flag = True; b = b+2; continue
						if int(response[b+1]) == 0:
							O.self_flag = False; b = b+2; continue
					else:
						try:
							p_value = float(response[b+1])
						except:
							try:
								p_value = int(response[b+1])
							except:
								p_value = str(response[b+1])
						#print "Props value:",response[b], p_value
						O.set_concrete_var(response[b], p_value); b += 2
		if O.name =="visual":
			if O.colour !="hand":
				self.add_observation(worldstate, O)
		else:
			self.add_observation(worldstate, O)
		return worldstate


	def add_observation(self, ws, o):
		found = False
		for o2 in self.observations:
			if not o2.is_generalised():
				if o2.name == o.name and o2.similar(o):
					#print "Observation previsously recorded1:", o.to_string(), o2.to_string()
					o.id = int(o2.id)
					found  = True; break
			else:
				 if o2.name == o.name and o2.equivalents(o):
					#print "Observation previsously recorded2:", o.to_string(), o2.to_string()
					o.id = int(o2.id)
					found  = True; break
		if not found:
			#print "Adding new observation in system:", o.to_string(), self.id
			o.id = int(self.id); self.id +=1
			self.observations.append(o)
		ws.add_observation(o)


	def send_command(self, command):
		"""Send a command to the RPC controller."""
		query = yarp.Bottle()
		query.clear()
		response = yarp.Bottle()
		response.clear()
		print ("sending %s in send_command"%command)
		query.addString(command)
		self.portactsender.write(query)
		response = self.portactstatusreceiver.read(True)
		return response.toString == "SUCCESS"


	def update_total_schemas(self):
		"""Update the label in the bottom right
		displaying the total number of schemas
		in the memory."""
		self.total = self.memory.get_total_schemas()

		self.totalSchemas.set_text(str(self.total))






	def show_request(self, caller=None):
		"""Display the world state request window."""
		self.requestWin.show()
		self.requestWin.present()


	def clear(self, caller=None):
		"""Clear the world state request output."""
		self.requestState = WorldState()
		self.requestTxt.set_text("")
		self.showBtn.set_sensitive(False)
		self.executeBtn.set_sensitive(False)
		self.path = None


	def add(self, caller=None):
		"""Adds an observation to the target
		world state from the GUI. Used for
		constructing targets for chains."""
		otype = self.builder.get_object("cmbObservation").get_active_text()
		o = Observation()
		o.name = otype
		properties = o.get_properties()
		dlg = None
		"""if otype == "Stack":
			dlg = self.builder.get_object("msgProperty")
			dlg.set_transient_for(self.requestWin)
			dlg.set_property("text", "Number of objects:")
			dlg.run()
			objs = int(self.builder.get_object("entProperty").get_text())
			for i in range(0, objs):
				self.builder.get_object("entProperty").set_text("")
				self.builder.get_object("entProperty").grab_focus()
				dlg.set_property("text", "Object %d:" % i)
				dlg.run()
				value = self.builder.get_object("entProperty").get_text()
				o.set_concrete_var("object%d"%i, value)
		else:"""
		dlg = self.builder.get_object("msgProperty")
		dlg.set_transient_for(self.requestWin)
		dlg.set_property("text", "Enter properties and values")
		dlg.run()
		value = self.builder.get_object("entProperty").get_text()
		self.builder.get_object("entProperty").set_text("")
		self.builder.get_object("entProperty").grab_focus()
		value = value.split(); m = 0
		while m<len(value):
			#print "M & values:", m, value[m], value[m+1]
			o.set_concrete_var(value[m], value[m+1])
			m = m+2
		if dlg:
			dlg.hide()
		self.requestState.add_observation(o)
		self.requestTxt.set_text("Current state to request:\n\n%s" % self.requestState.to_string())
		self.showBtn.set_sensitive(True)
		self.executeBtn.set_sensitive(True)


	def show_plan(self, caller=None):
		"""Finds a chain of actions leading to
		the target state specified in self.requestState
		and displays it in the GUI."""
		ws = self.get_sensors()
		self.path = self.memory.find_path(ws, self.requestState, [], False)
		if len(self.path) == 0:
			self.requestTxt.set_text("Unable to find a chain that leads to:\n\n%s" % self.requestState.to_string())
		else:
			output = "Found path:\n\n"
			for s in self.path:
				schema = self.memory.get_schema_from_id(s)
				output += "%s\n" % schema.to_string()
			self.requestTxt.set_text(output)


	def execute(self, caller=None):
		"""Executes the chain of actions necessary to
		achieve the target world state specified in
		self.requestState. May be called from either
		the GUI or from the RPC server."""

		status = self.memory.update_world_state(self.get_sensors())
		print "Execute Update state:",status
		if self.path == None:
			self.show_plan()
		while len(self.path) > 0:
			self.step_plan()


	def step_plan(self, caller=None):
		"""Executes a single step in a chain of schemas
		leading to the self.requestState"""

		self.memory.update_world_state(self.get_sensors())
		if self.path == None:
			self.show_plan()
		self.path = self.memory.execute_sequence_step(self.path, self.requestState)



	def checkRPC(self):
		#Runs as a separate thread waiting for input on
		#the RPC port. This input should take the form of a
		#desired world state in the same format as the
		#sensor output provided by the SMC RPC Controller.

		while self.running:
			cmd = yarp.Bottle()
			#self.rpcPort.read(cmd, False)
			#self.requestState = self.construct_worldstate(cmd).to_string()
			self.emit("executeChain")

	def quit(self, caller=None):
		self.running = False
		print "YARP Clean"
		os.system("yarp clean")
		self.portactsender.close()
		self.portactreceiver.close()
		self.portactstatusreceiver.close
		self.portstatereceiver.close()
		Gtk.main_quit()


if __name__ == '__main__':
	Controller()
	Gtk.main()