import sys
sys.path.append('D:\Carla0915\carla\PythonAPI\carla')

from agents.navigation.basic_agent import BasicAgent
from agents.tools.misc import *
import py_trees
from py_trees import behaviour, common

import RoadSearch
from agents.navigation.local_planner import RoadOption

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

import json
from ModelLoader import InternLM3
model = InternLM3()


class TimeControlBehaviour(py_trees.behaviour.Behaviour):
    """
    A behaviour that controls the time of the simulation.
    """

    def __init__(self, name, agent, duration=0.0, function_name=None, args=None):
        super(TimeControlBehaviour, self).__init__(name)
        self._agent = agent
        self._duration = args["duration"]
        self._first_update = True
        self._time_start = None
        self._function_name = function_name
        self._args = args

    def update(self):
        if self._first_update:
            
            self._time_start = self._agent.get_world().get_snapshot().timestamp.elapsed_seconds
            self._first_update = False
            method = getattr(self._agent, self._function_name)
            # print(self._args)
            method(**self._args) 
        
        time_now = self._agent.get_world().get_snapshot().timestamp.elapsed_seconds
        if time_now - self._time_start >= self._duration:
            return py_trees.common.Status.SUCCESS            
        return py_trees.common.Status.RUNNING
    
class PathFollowBehavior(py_trees.behaviour.Behaviour):
    """
    A basic agent that uses the Carla API to control a vehicle.
    """

    def __init__(self, name, agent, function_name=None, args=None):
        super(PathFollowBehavior, self).__init__(name)
        self._agent = agent
        self._first_update = True
        self._function_name = function_name
        self._args = args
        
    def update(self):
        if self._first_update:
            method = getattr(self._agent, self.function_name, None)
            method(*self._args)
            self._first_update = False
        if self._local_planner.done():
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING
    
    
class BehaviorTreeAgent(BasicAgent):
    def __init__(self, vehicle, target_speed=20, opt_dict={'_ignore_vehicles': True}, map_inst=None, grp_inst=None, behaviour_description=None):
        super().__init__(vehicle, target_speed, opt_dict, map_inst, grp_inst)
        ## .. 
        self._behavior_description = behaviour_description
        self._behavior_tree = None
        self.construct_behavior_tree()

    def get_world(self):
        return self._vehicle.get_world()
        
        
    def construct_behavior_tree(self):
        behaviour_description = self._behavior_description
        prompt = """The following text describes the driving behavior of a vehicle. 
                Please understand the vehicle's driving behavior and convert it into the form of a JSON document.
                Driving behavior of the vehicle is : {behaviour_description}
                
                Please note: only the following function_name are allowed.
                {tools_string}
                The args represents the corresponding parameters of the function you choose.
                Output only the final JSON object in the correct structure. Do not include any additional text or explanation.
                Please refer to the example below for guidance.
                {example_input}
                All fields shown in the example must be strictly included in your output JSON object.
                """
        example_dict = {
                    "sequence": [
                        {
                            "name": "WaitingForStart",
                            "duration": 2.0,
                            "function_name": "stop_for_time",
                            "args": {"duration":5.0}
                        },
                        {
                            "name": "AccelerateToSpeed",
                            "duration": 3.0,
                            "function_name": "accelerate_to_speed",
                            "args": {"target_speed":20.0, "duration":3.0}
                        },
                        {
                            "name": "GoStraight",
                            "duration": 4.0,
                            "function_name": "keep_in_lane",
                            "args": {"target_speed":20.0, "duration":4.0}
                        },
                        {
                            "name": "StopForTime",
                            "duration": 3.0,
                            "function_name": "stop_for_time",
                            "args": {"duration":5.0}
                        },
                        {
                            "name": "GoStraight",
                            "duration": 5.0,
                            "function_name": "keep_in_lane",
                            "args": {"target_speed":20.0, "duration":5.0}
                        }
                    ]
                }
        example_str = json.dumps(example_dict, indent=4)

        #tools = [self.accelerate_to_speed, self.deccelerate_to_speed, self.keep_in_lane,self.change_lane_left, self.change_lane_right, self.stop_for_time]
        tools_string = """accelerate_to_speed - Use this method to accelerate to a target speed for a certain duration.
                          deccelerate_to_speed - Use this method to deccelerate to a target speed for a certain duration.
                          keep_in_lane - Use this method to keep the vehicle in lane for a certain duration.
                          change_lane_left - Use this method to change lane to the left for a certain duration.
                          change_lane_right - Use this method to change lane to the right for a certain duration.
                          stop_for_time - Use this method to stop the vehicle for a certain duration.
                        """
        
        prompt = PromptTemplate.from_template(prompt)
        parser = JsonOutputParser()
        chain = prompt | model | parser


        res = chain.invoke({"behaviour_description": behaviour_description, "tools_string":tools_string, "example_input":example_str})

        # print(res)

        root_node_name = "root"
        behaviours = res['sequence']

        root_node = py_trees.composites.Sequence(root_node_name, memory=True)

        child_node = TimeControlBehaviour("wait_for_start", self, duration=3.0, function_name="stop_for_time", args={"duration":3.0})
        root_node.add_child(child_node)
        for behaviour in behaviours:
            behaviour_name = behaviour['name']
            duration = behaviour['duration']
            function_name = behaviour['function_name']
            args = behaviour['args']
            child_node = TimeControlBehaviour(behaviour_name, self, duration=duration, function_name=function_name, args=args)
            root_node.add_child(child_node)
        self._behavior_tree = py_trees.trees.BehaviourTree(root_node)
        
    def run_step(self):
        self._behavior_tree.tick()
        control = self._local_planner.run_step()
        self._vehicle.apply_control(control)

    ## Tools for behavior tree to call once
    def accelerate_to_speed(self, target_speed=20.0, duration=5.0):
        """Use this method to accelerate to a target speed for a certain duration."""
        distance = target_speed * duration / (7.2) 
        current_location = self._vehicle.get_transform().location
        num = int(distance / 2.0) + 1
        wps = RoadSearch.find_wp_next_location(self._map, current_location, num=num, distance=2)
        path_paln = [(wp, RoadOption.VOID) for wp in wps]
        self.set_target_speed(target_speed)
        self._local_planner.set_global_plan(path_paln)
    
    
    def deccelerate_to_speed(self, target_speed=20.0, duration=5.0):
        """Use this method to deccelerate to a target speed for a certain duration."""
        distance = target_speed * duration / (7.2) + 20.0
        current_location = self._vehicle.get_transform().location
        num = int(distance / 2.0) + 1
        wps = RoadSearch.find_wp_next_location(self._map, current_location, num=num, distance=2)
        path_paln = [(wp, RoadOption.VOID) for wp in wps]
        self.set_target_speed(target_speed)
        self._local_planner.set_global_plan(path_paln)    
   
    def keep_in_lane(self, target_speed=20.0, duration=5.0):
        """Use this method to keep in lane with a target speed for a certain duration."""
        distance = target_speed * duration / 3.6
        current_location = self._vehicle.get_transform().location
        num = int(distance / 2.0) + 1
        wps = RoadSearch.find_wp_next_location(self._map, current_location, num=num, distance=2)
        path_paln = [(wp, RoadOption.VOID) for wp in wps]
        self.set_target_speed(target_speed)
        self._local_planner.set_global_plan(path_paln)

    
    def change_lane_left(self, target_speed=20.0, duration=5.0):
        """Use this method to change lane to the left with a target speed for a certain duration."""
        path = self._generate_lane_change_path(
            self._map.get_waypoint(self._vehicle.get_location()),
            'left',
            5,
            5,
            5,
            False,
            1,
            self._sampling_resolution
        )
        self._local_planner.set_global_plan(path)
        self.set_target_speed(target_speed)

    
    def change_lane_right(self, target_speed=20.0, duration=5.0):
        """Use this method to change lane to the left with a target speed for a certain duration."""
        path = self._generate_lane_change_path(
            self._map.get_waypoint(self._vehicle.get_location()),
            'right',
            5,
            5,
            5,
            False,
            1,
            self._sampling_resolution
        )
        self._local_planner.set_global_plan(path)
        self.set_target_speed(target_speed)

    def stop_for_time(self, duration=5.0):
        """Use this method to stop for a certain duration."""
        self.set_target_speed(0.0)


class PedestrianAgent():
    def __init__(self, walker, target_locs, target_speed=1.0, behavior_description=None):
        
        self._walker = walker
        self._target_locs = target_locs
        self._target_speed = target_speed
        self._behavior_description = behavior_description
        self._behavior_tree = None

        #self.setup_controller()
        self.construct_behavior_tree()

    def get_world(self):
        return self._walker.get_world()
    def setup_controller(self):
        carla_world = self._walker.get_world()
        controller_bp = carla_world.get_blueprint_library().find('controller.ai.walker')
        self._controller = carla_world.spawn_actor(controller_bp, carla.Transform(), self._walker)
        self._controller.set_max_speed(self._target_speed)

    def construct_behavior_tree(self):
        prompt = """The following text describes the driving behavior of a pedestrian.
                    {behaviour_description}
                    Please understand the pedestrian's behavior and convert it into the form of a JSON document.
                    Please note: only the following function_name are allowed.
                    {tools_string}
                    Please refer to the example below for guidance.
                    {example_input}
                    The args represents the corresponding parameters of the function you choose.
                    Output only the final JSON object in the correct structure. Do not include any additional text or explanation.
                    All fields shown in the example must be strictly included in your output JSON object.
                 """
        tools_string = """go_to_target - Use this method to go to a target location for a certain duration.
                          stop_for_time - Use this method to stop for a certain duration.
                        """
        example_dict = {"sequence": [
            {
                "name": "GoToTarget",
                "duration": 5.0,
                "function_name": "go_to_target",
                "args": {"target_index": 0, "duration": 5.0, "target_speed": 1.0}
            },
            {
                "name": "WaitForTime",
                "duration": 3.0,
                "function_name": "stop_for_time",
                "args": {"duration": 5.0}
            },
            {
                "name": "GoToTarget",
                "duration": 5.0,
                "function_name": "go_to_target",
                "args": {"target_index": 1, "duration": 5.0, "target_speed": 1.0}
            }]}
        example_str = json.dumps(example_dict, indent=4)
        prompt = PromptTemplate.from_template(prompt)
        parser = JsonOutputParser()
        chain = prompt | model | parser

        res = chain.invoke({"behaviour_description": self._behavior_description, "tools_string":tools_string, "example_input":example_str})
        
        root_node_name = "root"
        behaviours = res['sequence']
        print(behaviours)
        root_node = py_trees.composites.Sequence(root_node_name, memory=True)

        child_node = TimeControlBehaviour("wait_for_start", self, duration=3.0, function_name="stop_for_time", args={"duration":3.0})
        root_node.add_child(child_node)
        for behaviour in behaviours:
            behaviour_name = behaviour['name']
            #duration = behaviour['duration']
            function_name = behaviour['function_name']
            args = behaviour['args']
            child_node = TimeControlBehaviour(behaviour_name, self, function_name=function_name, args=args)
            root_node.add_child(child_node)
        self._behavior_tree = py_trees.trees.BehaviourTree(root_node)
    def run_step(self):
        self._behavior_tree.tick()

    # tools function of walkers
    def go_to_target(self, target_index=0, duration=5.0, target_speed=1.0):
        """Use this method to go to a target location for a certain duration."""
        current_location = self._walker.get_transform().location
        target_location = self._target_locs[target_index]
        direction = target_location - current_location
        walk_control = carla.WalkerControl()    
        walk_control.direction = direction
        walk_control.speed = target_speed
        self._walker.apply_control(walk_control)
        # self._controller.go_to_location(target_location)
        # self._controller.set_max_speed(target_speed)
        # self._controller.start()

    def stop_for_time(self, duration=5.0):
        """Use this method to stop for a certain duration."""
        walk_control = carla.WalkerControl()
        walk_control.speed = 0.0
        self._walker.apply_control(walk_control)