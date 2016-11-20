__author__ = 'mmmmmtasty'

from soco import SoCo
import json
import time
#from scapy.all import *
import os
import traceback
from email.mime.text import MIMEText
from smtplib import SMTP
from qhue import Bridge, QhueException, create_new_username

# Send an email alert
def send_email_alert(subject, body):

    # Get variables
    to_addr = config['email']['to']
    from_addr = config['email']['from']
    relay = config['email']['easy_smtp_relay']
    user = config['email']['easy_smtp_user']
    password = config['email']['easy_smtp_pass']

    # Create a text/plain message
    if body:
        msg = MIMEText(body)
    else:
        msg = MIMEText("Someone has turned up at your door!")

    msg['To'] = to_addr
    msg['From'] = from_addr
    msg['Subject'] = subject

    # Send email
    conn = SMTP(relay, 587)
    conn.set_debuglevel(False)
    conn.ehlo()
    conn.starttls() # Omit if SMTPSg
    conn.ehlo() # Omit if SMTPSg
    conn.login(user, password)

    try:
        conn.sendmail(from_addr, to_addr, msg.as_string())
    finally:
        conn.quit()

# Get modified time of given relative file path
def get_mod_time(file_path):
    # Get relative path for state
    dir = os.path.dirname(__file__)
    full_filename = os.path.join(dir, file_path)

    # Return modified time
    return os.path.getmtime(full_filename)

# Load json from given path
def load_json(config_path):
    # Try and load the config
    try:
        # Get relative path for config
        dir = os.path.dirname(__file__)
        filename = os.path.join(dir, config_path)

        # Load configuration
        with open(filename) as file:
            return json.load(file)
    except:
        error = "Exception while loading json file: {0}".format(traceback.format_exc())
        print error
        if config['general']['email_alert']:
            send_email_alert("Exception thrown loading json file in doorbell.py", error)
        exit("Terminating error!")

# Convert times in 00:00:00 format to an integer number of seconds
def time_to_int( time ):
    accum = 0
    mult = 1
    for p in reversed(time.split(':')):
        accum += (int(p)*mult)
        mult *= 60
    return accum

# Convert integer number of seconds to time in 00:00:00 format
def int_to_time( time ):
    temp_minutes, seconds = divmod(time, 60)
    hours, minutes =  divmod(temp_minutes, 60)
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)

# Alert on the sonos system
def alert_sonos(sonos_state, coordinator, group_players, uri, volume):

    # Play sounds - the volume or mute status may need adjusting, but if we do it too quick the music gets the volume change
    coordinator.play_uri(uri)

    # It the sonos is muted, unmute and set the volume to a reasonable level
    for player in group_players:
        print "Checking mute status of {0}".format(player.player_name)
        if sonos_state[player.player_name]['mute']:
            print "Unmuting player: {0}".format(coordinator.player_name)
            player.mute = False

        print "Checking volume level for {0}".format(player.player_name)
        if sonos_state[player.player_name]['volume'] != 10:
            print "Setting volume to 10 for {0}".format(player.player_name)
            player.volume = config['sonos']['volume']

    # Time to resume playing the sonos
    return int(time.time()) + time_to_int(coordinator.get_current_track_info()['duration'])

def reset_sonos(sonos_state, coordinator, group_players):
    # It the sonos was muted, mute again
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
            seek_time = int_to_time(current_track_position_secs - sonos_state[coordinator.player_name]['track']['track_duration'])
            playlist_position = int(sonos_state[coordinator.player_name]["track"]['playlist_position'])
        else:
            seek_time = int_to_time(current_track_position_secs)
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

# Play
def play_doorbell():
    print "Playing doorbell alerts"
    # Start playing the sound on the sonos player
    if config['general']['sonos_alert']:
        # Load the current state
        print "Loading current state file from {0}".format(config['sonos']['state_file_path'])
        sonos_state = load_json(config['sonos']['state_file_path'])

        # TODO: Allow definition of multiple sonos players to use

        # Get coordinator of group
        coordinator = SoCo(sonos_state[sonos_state[config['sonos']['player_name']]['group_coordinator']]['ip_address'])
        group_players = coordinator.group.members

        restart_time = alert_sonos(sonos_state, coordinator, group_players, config['sonos']['doorbell_uri'], config['sonos']['volume'] )

    # Alert with hue lights if we need to
    try:
        if config['general']['hue_alert']:
            # Get bridge
            bridge = Bridge(config['hue']['bridge_ip'], config['hue']['bridge_user'])
            # 'Breathe'lights once
            bridge.groups[0].action(alert='select')
    except:
        error = "Exception while controlling hue lights: {0}".format(traceback.format_exc())
        print error
        if config['general']['email_alert']:
            send_email_alert("Exception thrown alerting hue lights doorbell.py", error)

    # Take a photo if we need to
    # TODO: Take photo and send it in email

    # Send email alert if we need to
    # TODO: Send email alert, include link to photo or streaming video if needed

    # Set the state of the sonos back to what it was previously
    if config['general']['sonos_alert']:
        # Make sure the sound has finished playing
        while restart_time > int(time.time()):
            time.sleep(1)
        reset_sonos(sonos_state, coordinator, group_players)


# Method to inspect packets to find the relevant ARP from the doorbell
def arp_display(pkt):
    if pkt.haslayer(ARP):
        if pkt[ARP].op == 1: #who-has (request)
            if pkt[ARP].hwsrc == config['amazon_dash']['mac_address']:
                play_doorbell()
            else:
                print pkt[ARP].hwsrc




# TODO: Reload configuration if the modified time has changed

config_relative_path = 'config/doorbell_config.json'

# Load the config
try:
    config = load_json(config_relative_path)
    config_mod_time = get_mod_time(config_relative_path)
except:
    error = "Exception while reading config: {0}".format(traceback.print_exc())
    print error
    if config['general']['email_alert']:
        send_email_alert("Exception thrown loading config in doorbell.py", error)

#while True:
#    try:
#        sniff(prn=arp_display, filter="arp", store=0, count=0)
#    except:
#        error = "Exception while reading config: {0}".format(traceback.print_exc())
#        print error
#        if config['general']['email_alert']:
#            send_email_alert("Exception thrown scanning for ARP packets in doorbell.py", error)
#        time.sleep(30)

play_doorbell()