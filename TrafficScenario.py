

import carla
import time
import random
import json
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from BehaviorTreeAgent import BehaviorTreeAgent, PedestrianAgent

from ModelLoader import InternLM3
model = InternLM3()

class TrafficScenario(object):
    def __init__(self, client, world, scenario_description: dict, scenario_input: str):
        self._client = client
        self._world = world
        self._scenario_description = scenario_description
        self._ego = None
        self._ego_transform = None
        self._ego_behaviour_agent = None

        self._npc_vehicles = []
        self._npc_vehicles_transforms= [] 
        self._npc_vehicles_behaviour_agents = []

        self._pedestrians = []
        self._pedestrians_transforms = []
        self._pedestrians_targets = []
        self._pedestrians_behaviour_agents = []
        
        self._name = None
        self._scenario_input = scenario_input

        self._name_str = []
        self._name_actors = {}
        self._name_targets = {}

        self.load_map()
        self.setup_weather()
        self.spawn_actors()
        self.generate_agents()

        
    def load_map(self):
        self._map = self._scenario_description['map']
        maps = self._client.get_available_maps()
        for map in maps:
            if map.endswith(self._map):
                self._client.load_world(map)
                break
        time.sleep(5.0)

    def setup_weather(self):
        pass

    def spawn_actors(self):
        self._name = self._scenario_description['name']
        
        self._description = self._scenario_description['description']

        for  item in self._scenario_description['placement']:
            name = item['name']
            self._name_str.append(name)
            if name.startswith("ego"):
                print("Teleporting ego:", name)
                spawn_point = item['spawn_point']
                self._ego_transform = carla.Transform(carla.Location(x=spawn_point['x']/100.0, y=spawn_point['y']/100.0, z=spawn_point['z']/100.0), carla.Rotation(pitch=spawn_point['pitch'], yaw=spawn_point['yaw'], roll=spawn_point['roll']))
                self._world.player.set_transform(self._ego_transform)
                self._name_actors[name] = self._world.player

                target_locations = []
                if 'target' in item:
                    for target in item['target']:
                        target_location = carla.Location(x=target['x']/100.0, y=target['y']/100.0, z=target['z']/100.0)
                        target_locations.append(target_location)
                    self._name_targets[name] = target_locations
            if name.startswith("npc_vehicle"):
                print("Spawning npc:", name)
                spawn_point = item['spawn_point']
                v_transfrom = carla.Transform(carla.Location(x=spawn_point['x']/100.0, y=spawn_point['y']/100.0, z=spawn_point['z']/100.0), carla.Rotation(pitch=spawn_point['pitch'], yaw=spawn_point['yaw'], roll=spawn_point['roll']))
                bps = self._world.world.get_blueprint_library().filter("vehicle.bmw.*")
                npc_vehicle = self._world.world.spawn_actor(bps[0], v_transfrom)
                self._name_actors[name] = npc_vehicle
                self._npc_vehicles_transforms.append(v_transfrom)
                self._npc_vehicles.append(npc_vehicle)
                
                target_locations = []
                if 'target' in item:
                    for target in item['target']:
                        target_location = carla.Location(x=target['x']/100.0, y=target['y']/100.0, z=target['z']/100.0)
                        target_locations.append(target_location)
                    self._name_targets[name] = target_locations

            if name.startswith("pedestrian"):
                spawn_point = item['spawn_point']
                p_transform = carla.Transform(carla.Location(x=spawn_point['x']/100.0, y=spawn_point['y']/100.0, z=spawn_point['z']/100.0), carla.Rotation(pitch=spawn_point['pitch'], yaw=spawn_point['yaw'], roll=spawn_point['roll']))
                bps = self._world.world.get_blueprint_library().filter("walker.pedestrian.*")
                pedestrian = self._world.world.spawn_actor(random.choice(bps), p_transform)
                self._name_actors[name] = pedestrian

                self._pedestrians_transforms.append(carla.Transform(carla.Location(x=spawn_point['x']/100.0, y=spawn_point['y']/100.0, z=spawn_point['z']/100.0), carla.Rotation(pitch=spawn_point['pitch'], yaw=spawn_point['yaw'], roll=spawn_point['roll'])))
                self._pedestrians.append(pedestrian)
                target_locations = []
                for target in item['target']:
                    target_location = carla.Location(x=target['x']/100.0, y=target['y']/100.0, z=target['z']/100.0)
                    target_locations.append(target_location)
                self._pedestrians_targets.append(target_locations)
                self._name_targets[name] = target_locations

    def generate_agents(self):
        """Generating behaviour agents for ego and npc vehicles"""
        print("Generating agents...")
        names = ','.join(self._name_str)
        print(names)
        prompt = """ 
                Generate  motion plan for each actor based on the following description.
                Description:
                {info}.
                Actors in scenario include:{names}.
                Dont include any other actors that are not in the scenario.
                Please note There are two styles of vehicle behavior. 
                The style1 uses only duration and speed, as vehicle_1 in the example. 
                The style2 uses only target locations and speed, as vehicle_2 in the example.
                Must choose the style vehicle's behavior, then generate.
                Here is a example: {example}
                Output only the final JSON object in the correct structure. Do not include any additional text or explanation.
                """
        example_dict = {
            "vehicle_1":{
                "style1_vehicle":1,
                "behavior":"Accelerate to 20 km/h for 5 seconds. Then keep the lane for 5 seconds. Decelerate to 0 km/h for 5 seconds. Stop for 5 seconds."},
            "vehicle_2":{
                "style2_vehicle":2,
                "behavior":"Go to target 0 with speed 20km/h,then target 1 with speed 20km/h , then target 2 with speed 20km/h "},
            "pedestrian_1":"Go to target 0, then target 1 with speed 1.0 m/s"
        }
        example_str = json.dumps(example_dict, indent=4)
        prompt = PromptTemplate.from_template(prompt)
        parser = JsonOutputParser()
        chain = prompt | model | parser
        res = chain.invoke({"info": self._scenario_input, "names":names, "example": example_str})

        #print("res_agent:", res)
        #print("_name_targets:", self._name_targets)
        for key, value in res.items():
            if key.startswith("ego"):
                targets = None
                if key in self._name_targets:
                    targets = self._name_targets[key]
                vehicle = self._name_actors[key]
                bt_agent = BehaviorTreeAgent(vehicle, behaviour_description=value['behavior'], target_locations=targets)
                self._ego_behaviour_agent = bt_agent
            if key.startswith("npc"):
                targets = None
                if key in self._name_targets:
                    targets = self._name_targets[key]
                vehicle = self._name_actors[key]
                bt_agent = BehaviorTreeAgent(vehicle, behaviour_description=value['behavior'], target_locations=targets)
                self._npc_vehicles_behaviour_agents.append(bt_agent)
            if key.startswith("pedestrian"):
                pedestrian = self._name_actors[key]
                targets = self._name_targets[key]
                bt_agent = PedestrianAgent(pedestrian, targets, target_speed=1.0, behavior_description=value)
                self._pedestrians_behaviour_agents.append(bt_agent)
                                                                       
    def run_step(self):
        self._ego_behaviour_agent.run_step()
        
        for npc_agent in self._npc_vehicles_behaviour_agents:
            npc_agent.run_step()
        for pedestrian_agent in self._pedestrians_behaviour_agents:
            pedestrian_agent.run_step()
            
    def end_scenario(self):
        for vehicle in self._npc_vehicles:
            vehicle.destroy()
        for pedestrian in self._pedestrians:
            pedestrian.destroy()
        