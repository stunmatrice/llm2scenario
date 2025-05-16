import carla
import sys
from LLM2Scenario import client
from langchain_core.tools import tool

sys.path.append('D:\Carla0915\carla\PythonAPI\carla')

import agents.tools.misc as misc

# def find_wp_from_lane_start(carla_map, distance=100.0):
#     transforms = carla_map.get_spawn_points()
#     for trans in transforms:
#         driving_wp = carla_map.get_waypoint(trans.location, project_to_road=True, lane_type=carla.LaneType.Driving)
    
# Search next waypoints from waypoint
def find_wp_next(carla_wp, num=10, distance=2.0):
    wps = []
    wp_index = carla_wp
    for i in range(num):
        wps.append(wp_index.next(distance)[0])
        wp_index = wps[-1]
    return wps

# Search previous waypoints from waypoint
def find_wp_previous(carla_wp, num=10, distance=2.0):
    wps = []
    wp_index = carla_wp
    for i in range(num):
        wps.append(wp_index.previous(distance)[0])
        wp_index = wps[-1]
    return wps


# Search next waypoints from location
def find_wp_next_location(carla_map, carla_location, num=10, distance=2.0):
    wps = []
    carla_wp = carla_map.get_waypoint(carla_location, project_to_road=True, lane_type=carla.LaneType.Driving)
    wp_index = carla_wp
    for i in range(num):
        wps.append(wp_index.next(distance)[0])
        wp_index = wps[-1]
    return wps

def replan_wp(carla_wp, num=10, distance=2.0):
    wps = []
    for i in range(num):
        wps.append(carla_wp.next(distance)[0])
    return wps

# Find the waypoint with parking space
# The function returns the waypoint and the parking space waypoint
def find_wp_with_parking(carla_map, s=1.0):
    transforms = carla_map.get_spawn_points()
    postions = None
    for trans in transforms:
        driving_wp = carla_map.get_waypoint(trans.location, project_to_road=True, lane_type=carla.LaneType.Driving)
        wp_start = carla_map.get_waypoint_xodr(driving_wp.road_id, driving_wp.lane_id, s)
        if wp_start is None:
            continue
        parking_wp = carla_map.get_waypoint(wp_start.transform.location, project_to_road=True, lane_type=carla.LaneType.Stop)
        
        if parking_wp is not None:
            print(parking_wp)
            if parking_wp.road_id == driving_wp.road_id and abs(parking_wp.lane_id - driving_wp.lane_id) == 1 and parking_wp.section_id == driving_wp.section_id:
                postions = (wp_start, parking_wp)
                break
            else:
                continue
        else:
            continue
    return postions

# Find the waypoint before the junction
# def find_wp_with_sidewalk_ahead(carla_map, distance=20.0):
#     transforms = carla_map.get_spawn_points()
    

#     wps = []
#     carla_wp = carla_map.get_waypoint(carla_location, project_to_road=True, lane_type=carla.LaneType.Driving)
#     wp_index = carla_wp
#     for i in range(num):
#         wps.append(wp_index.previous(distance)[0])
#         wp_index = wps[-1]
#     return wps





## Add fix spawn points for town10
def town10_car_pedestrian_location_pairs(carla_map):
    lx = -4856.546875
    ly = 8564.511719
    lz = 60.0
    return carla.Location(x=lx, y=ly, z=lz)



def town10_parking_ahead_pair(carla_map):
    # UE editor uses cm 
    # Carla uses m
    lx1 = 6150.0 / 100.0
    ly1 = 6630.0 / 100.0
    lz1 = 60.0 / 100.0
    loc1 = carla.Location(x=lx1, y=ly1, z=lz1)

    lx2 = 1560.0 / 100.0
    ly2 = 6340.0 / 100.0
    lz2 = 60.0 / 100.0

    wp1 = carla_map.get_waypoint(loc1, project_to_road=True, lane_type=carla.LaneType.Driving)
    trans2 = carla.Transform(carla.Location(x=lx2, y=ly2, z=lz2), wp1.transform.rotation)
    return (wp1.transform, trans2)


def pedstrian_location_pairs(carla_map):
    lx = -4856.546875
    ly = 8564.511719
    lz = 60.0
    return carla.Location(x=lx, y=ly, z=lz)


def town10_pedestrian_location_pairs(carla_map, number=10):
    
    startx = 11790.0 / 100.0
    starty = 3360.0 / 100.0
    startz = 2.0

    endx = 8510.0 / 100.0
    endy = 3460.0 / 100.0
    endz = 2.0

    #
    start_locs = [carla.Location(x=startx, y=starty, z=startz)]
    dest_locs = [carla.Location(x=endx, y=endy, z=endz)] 
    
    start_trans = [carla.Transform(loc, carla.Rotation(pitch=0, yaw=0, roll=0)) for loc in start_locs]
    dest_trans = [carla.Transform(loc , carla.Rotation(pitch=0, yaw=0, roll=0)) for loc in dest_locs]
    return (start_trans, dest_trans)


class RoadSearch(object):
    def __init__(self, carla_map):
        self._carla_map = carla_map
    
    def seach_postions(self, scenario_description):
        prompt = f""""""
        client.chat.completions
        return 

    