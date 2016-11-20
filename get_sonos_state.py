__author__ = 'mmmmmtasty'

import soco
from soco import SoCo
import time
import json
import os
import traceback
from email.mime.text import MIMEText
from smtplib import SMTP


# Convert times in 00:00:00 format to an integer number of seconds
def time_to_int( time_string ):
    accum = 0
    mult = 1
    for p in reversed(time_string.split(':')):
        accum += (int(p)*mult)
        mult *= 60
    return accum


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
        error = "Exception while loading config: {0}".format(traceback.format_exc())
        print error
        if config['general']['email_alert']:
            send_email_alert("Exception thrown in get_sonos_state.py", error)
        exit("Terminating error!")


# Get modified time of given relative file path
def get_mod_time(file_path):
    # Get relative path for state
    dir = os.path.dirname(__file__)
    full_filename = os.path.join(dir, file_path)

    # Return modified time
    return os.path.getmtime(full_filename)


# Write out json object to relative file path
def write_json(json_obj, file_path):
    # Get relative path for state
    dir = os.path.dirname(__file__)
    full_filename = os.path.join(dir, file_path)

    state_json = json.dumps(json_obj, indent=4)
    f = open(full_filename, 'w')
    print >> f, state_json
    f.close()


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


# Get the current sonos state
def get_state(file_path):
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
            player_state['track']['track_position'] = time_to_int(track['position'])
        if track['duration'] == 'NOT_IMPLEMENTED':
            player_state['track']['track_duration'] = 'NOT_IMPLEMENTED'
        else:
            player_state['track']['track_duration'] = time_to_int(track['duration'])
        player_state['media_uri'] = track['uri']
        player_state['media_uri_metadata'] = track['metadata']

        player_state['time'] = int(time.time())

        # Save it in the global state
        sonos_state[player.player_name] = player_state

    print "Saving sonos state file"
    write_json(sonos_state, file_path)

config_relative_path = 'config/doorbell_config.json'

# Load the config
try:
    config = load_json(config_relative_path)
    config_mod_time = get_mod_time(config_relative_path)
except:
    error = "Exception while reading config: {0}".format(traceback.print_exc())
    print error
    if config['general']['email_alert']:
        send_email_alert("Exception thrown loading config in get_sonos_state.py", error)

while True:
    try:
        # Check to see if the config has been updated and reload if so
        latest_mod_time = get_mod_time(config_relative_path)
        if latest_mod_time > config_mod_time:
            config_mod_time = latest_mod_time
            config = load_json(config_relative_path)

        # Get the current state
        get_state(config['sonos']['state_file_path'])

        # Sleep until we need to get the information again
        time.sleep(config['sonos']['polling_interval_secs'])
    except:
        error = "Exception while getting Sonos state: {0}".format(traceback.format_exc())
        print error
        if config['general']['email_alert']:
            send_email_alert("Exception thrown in get_sonos_state.py", error)

        # Sleep until we need to get the information again
        time.sleep(config['sonos']['polling_interval_secs'])