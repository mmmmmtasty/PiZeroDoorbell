__author__ = 'mmmmmtasty'

import soco
from soco import SoCo
import json
import time
from scapy.all import *
import os

# Get relative path for config
dir = os.path.dirname(__file__)
filename = os.path.join(dir, '/config/doorbell_config.json')

# Load configuration
print "Loading config..."
with open(filename) as file:
    config = json.load(file)

# Convert times in 00:00:00 format to an integer number of seconds
def timeToInt( timeStr ):
    accum = 0
    mult = 1
    for p in reversed(timeStr.split(':')):
        accum += (int(p)*mult)
        mult *= 60
    return accum

# Convert integer number of seconds to time in 00:00:00 format
def intToTime( timeInt ):
    temp_minutes, seconds = divmod(timeInt, 60)
    hours, minutes =  divmod(temp_minutes, 60)
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)

# Play
def play_doorbell():
    # Load the current state
    print "Loading current state file from {0}".format(config['sonos_state_file_path'])
    with open(config['sonos_state_file_path']) as file:
        sonos_state = json.load(file)

    # Get coordinator of group
    coordinator = SoCo(sonos_state[sonos_state[config['doorbell_sonos']]['group_coordinator']]['ip_address'])
    group_players = coordinator.group.members

    # Play sounds - the volume or mute status may need adjusting, but if we do it too quick the music gets the volume change
    coordinator.play_uri(config['doorbell_uri'])

    # It the sonos is muted, unmute and set the volume to a reasonable level
    for player in group_players:
        print "Checking mute status of {0}".format(player.player_name)
        if sonos_state[player.player_name]['mute']:
            print "Unmuting player: {0}".format(coordinator.player_name)
            player.mute = False

        print "Checking volume level for {0}".format(player.player_name)
        if sonos_state[player.player_name]['volume'] != 10:
            print "Setting volume to 10 for {0}".format(player.player_name)
            player.volume = config['doorbell_volume']

    # Sleep until sound finishes
    time.sleep(timeToInt(coordinator.get_current_track_info()['duration']))

    # It the sonos is muted, unmute
    for player in group_players:
        print "Resetting mute status of {0}".format(player.player_name)
        if sonos_state[player.player_name]['mute']:
            print "Muting player: {0}".format(coordinator.player_name)
            player.mute = True
        print "Resetting volume level to {0} for {1}".format(sonos_state[player.player_name]['volume'], player.player_name)
        player.volume = sonos_state[player.player_name]['volume']

    # If the radio was playing before, play it again
    if sonos_state[coordinator.player_name]['radio']:
        print "Playing radio on {0}".format(coordinator.player_name)
        coordinator.play_uri(sonos_state[coordinator.player_name]['media_uri'], sonos_state[coordinator.player_name]['media_uri_metadata'] )

    # If the Sonos was playing TV before, play it again
    elif sonos_state[coordinator.player_name]['tv']:
        print "Playing TV on {0}".format(coordinator.player_name)
        coordinator.switch_to_tv()

    # If there was a playlist playing before, play it again
    elif sonos_state[coordinator.player_name]['track']['track_duration'] != 0:
        print "Playing queue on {0}".format(coordinator.player_name)
        # How long since the state file was generated and should the same song be playing now?
        secs_since_state = int(time.time()) - sonos_state[coordinator.player_name]['time']
        current_track_position_secs = sonos_state[coordinator.player_name]['track']['track_position'] + secs_since_state

        if current_track_position_secs > sonos_state[coordinator.player_name]['track']['track_duration']:
            seek_time = intToTime(current_track_position_secs - sonos_state[coordinator.player_name]['track']['track_duration'])
            playlist_position = int(sonos_state[coordinator.player_name]["track"]['playlist_position'])
        else:
            seek_time = intToTime(current_track_position_secs)
            playlist_position = int(sonos_state[coordinator.player_name]["track"]['playlist_position'])-1

        print "Seeking to {0} in playlist position {1}".format(seek_time, playlist_position)
        coordinator.play_from_queue(playlist_position)
        coordinator.seek(seek_time)

    # Set the status of the coordinator back to what it was previously.
    if sonos_state[coordinator.player_name]['play_state'] == 'STOPPED':
        print "Stopping music on {0}".format(coordinator.player_name)
        coordinator.stop()
    elif sonos_state[coordinator.player_name]['play_state'] == 'PAUSED':
        print "Pausing music on {0}".format(coordinator.player_name)
        coordinator.pause()

def arp_display(pkt):
    if pkt.haslayer(ARP):
        if pkt[ARP].op == 1: #who-has (request)
            if pkt[ARP].hwsrc == config['doorbell_mac']:
                play_doorbell()
            else:
                print pkt[ARP].hwsrc

sniff(prn=arp_display, filter="arp", store=0, count=0)
