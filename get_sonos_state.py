__author__ = 'mmmmmtasty'

import soco
from soco import SoCo
import time
import json
import os

# Convert times in 00:00:00 format to an integer number of seconds
def timeToInt( timeStr ):
    accum = 0
    mult = 1
    for p in reversed(timeStr.split(':')):
        accum += (int(p)*mult)
        mult *= 60
    return accum

# Get relative path for config
print os.path.dirname(__file__)
dir = os.path.dirname(__file__)
filename = os.path.join(dir, 'config/doorbell_config.json')
print filename

# Load configuration
with open(filename) as file:
    config = json.load(file)

# Constants
polling_interval_secs = config['polling_interval_secs']
sonos_state_file_path = config['sonos_state_file_path']

# Continually get state
while True:
    # New object for the current state of the sonos environment
    sonos_state = dict()

    # Get all players in the environment
    players = soco.discover()

    # Collect the relevant data for each of the players
    for player in players:
        print "Processing sonos: {0}".format(player.player_name)

        # Get all useful information for each sonos
        player_state = dict()

        player_state['play_state'] = player.get_current_transport_info()['current_transport_state']

        # Get information about sonos state
        player_state['ip_address'] = player.ip_address
        player_state['queue_size'] = player.queue_size
        player_state['volume'] = player.volume
        player_state['mute'] = player.mute
        player_state['tv'] = player.is_playing_tv
        player_state['radio'] = player.is_playing_radio
        player_state['group_coordinator'] = player.group.coordinator.player_name

        # Get information about track status
        track = player.get_current_track_info()
        player_state['track'] = dict()
        player_state['track']['playlist_position'] = track['playlist_position']
        if track['position'] == 'NOT_IMPLEMENTED':
            player_state['track']['track_position'] = 'NOT_IMPLEMENTED'
        else:
            player_state['track']['track_position'] = timeToInt(track['position'])
        if track['duration'] == 'NOT_IMPLEMENTED':
            player_state['track']['track_duration'] = 'NOT_IMPLEMENTED'
        else:
            player_state['track']['track_duration'] = timeToInt(track['duration'])
        player_state['media_uri'] = track['uri']
        player_state['media_uri_metadata'] = track['metadata']

        player_state['time'] = int(time.time())

        sonos_state[player.player_name] = player_state


    # Get relative path for state
    sonos_state_filename = os.path.join(dir, sonos_state_file_path)

    print "Saving sonos state file"
    state_json = json.dumps(sonos_state, indent=4)
    f = open(sonos_state_filename, 'w')
    print >> f, state_json
    f.close()

    # Sleep until we need to get the information again
    time.sleep(polling_interval_secs)

