
import argparse
import collections
import datetime
import glob
import logging
import math
import os
import numpy.random as random
import re
import sys
import weakref
# ==============================================================================
# -- Add PythonAPI for release mode --------------------------------------------
# ==============================================================================
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/carla')
except IndexError:
    pass

import carla
from carla import ColorConverter as cc

sys.path.append('D:\Carla0915\carla\PythonAPI\carla')

from TrafficScenario2 import TrafficScenario
import PlacementEmbedding


def game_loop(args):

    sim_world = None
    trafficScenario = None
    try:
        if args.seed:
            random.seed(args.seed)

        client = carla.Client(args.host, args.port)
        client.set_timeout(60.0)

        # traffic_manager = client.get_trafficmanager()
        sim_world = client.get_world()

        if args.sync:
            settings = sim_world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = 0.05
            sim_world.apply_settings(settings)

        
        ## 用户输入，来自于GUI输入框
#         behavior_description = """
#                             The ego vehicle accelerates to 20km/h in 2s, 
#                             then go straight in 25km/h for 9s, then decelerates to 0km upon approach in 2s, 
#                             and waits for 10 seconds, Then accelerates to 20km/h in 2s, then go straight for 15s, 
# . 
#                             npc vehicles 1 is  accelerating to 25km/h in 2s, then go straight in 25km/h for 8s, 
#                             then decelerates to 0km upon approach in 2s, and waits for 10 seconds until the pedestrians have passed,
#                             Then accelerates to 20km/h in 2s, then go straight for 15s.
                            
#                             pedestrian 1 is walking at 0.1m/s in 3s to target 0, then stop for 12s, then walk to target 1 at 0.1m/s in 10s,
#                             pedestrian 2 is walking at 0.1m/s in 5s to target 0, then stop for 10s, then walk to target 1 at 0.1m/s in 8s,
#                             pedestrian 3 is walking at 0.1m/s in 5s to target 0, then stop for 10s, then walk to target 1 at 0.1m/s in 8s.
#                             pedestrian 4 is walking at 0.1m/s in 5s to target 0, then stop for 10s, then walk to target 1 at 0.1m/s in 8s.
#                             """
        
        
        # For search
        scenario_description = """
                            The ego vehicle is going to change lane to the left,then merge to the ramp.
                            """
        # For generate behavior tree
        behavior_description = """
                            The ego vehicle accelerates to 20km/h in 1s, then keep in lane for 2s, then decelerates to 0km/s in 1s, then stop for 1s, then accelerate to 25km/h in 2s, then keep in lane for 15s in 25km/h.
                            npc1 stop stop for 3s, then goes to target0 with speed of 25 km/h, then keep in lane in 25km/h for 20s.
                            npc2 stop stopfor 2s, then goes to target0 with speed of 20 km/h, then keep in lane in 25km/h for 20s.
                            npc3 keep in lane in 20km/h for 20s,
                            npc4 keep in lane in 20km/h for 20s,
                            """

        # behavior_description = """
        #                     The ego vehicle goes to target0, then target1, then target2, then target3, then target4, with speed of 20 km/h,
        #                     npc vehicles 1 goes to target0,then target1, then target2, then target3, then target4, with speed of 20 km/h.
        #                     """
        
        
        ## 场景搜索，从向量数据库搜索一个最为匹配的场景Placement，用于初始化场景

        scenario_description_dict = PlacementEmbedding.load_placement_file2("D:\data_set\Scenario.jsonl")
        trafficScenario = TrafficScenario(client, sim_world, scenario_description_dict, behavior_description)

        ### --------------------------------------------------------

        

        
        while True:
            
            if args.sync:
                sim_world.tick()
            else:
                sim_world.wait_for_tick()

            sim_world.tick()


            trafficScenario.run_step()


    finally:

        if sim_world is not None:
            settings = sim_world.get_settings()
            settings.synchronous_mode = False
            settings.fixed_delta_seconds = None
            sim_world.apply_settings(settings)
            # traffic_manager.set_synchronous_mode(True)
            #sim_world.destroy()

            trafficScenario.end_scenario()


def main():
    """Main method"""

    argparser = argparse.ArgumentParser(
        description='CARLA Automatic Control Client')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='Print debug information')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1280x720',
        help='Window resolution (default: 1280x720)')
    argparser.add_argument(
        '--sync',
        action='store_true',
        help='Synchronous mode execution')
    argparser.add_argument(
        '--filter',
        metavar='PATTERN',
        default='vehicle.tesla.*',
        help='Actor filter (default: "vehicle.tesla.*")')
    argparser.add_argument(
        '--generation',
        metavar='G',
        default='2',
        help='restrict to certain actor generation (values: "1","2","All" - default: "2")')
    argparser.add_argument(
        '-l', '--loop',
        action='store_true',
        dest='loop',
        help='Sets a new random destination upon reaching the previous one (default: False)')
    argparser.add_argument(
        "-a", "--agent", type=str,
        choices=["Behavior", "Basic", "Constant"],
        help="select which agent to run",
        default="Behavior")
    argparser.add_argument(
        '-b', '--behavior', type=str,
        choices=["cautious", "normal", "aggressive"],
        help='Choose one of the possible agent behaviors (default: normal) ',
        default='normal')
    argparser.add_argument(
        '-s', '--seed',
        help='Set seed for repeating executions (default: None)',
        default=None,
        type=int)

    args = argparser.parse_args()

    args.width, args.height = [int(x) for x in args.res.split('x')]

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    logging.info('listening to server %s:%s', args.host, args.port)

    print(__doc__)

    try:
        game_loop(args)

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':
    main()