__author__ = 'mikjohnson'

import os
import qhue
from qhue import Bridge, QhueException, create_new_username
import json

# Get relative path for config
dir = os.path.dirname(__file__)
config_filename = os.path.join(dir, 'config/doorbell_config.json')

# Load configuration
print "Loading config..."
with open(config_filename) as file:
    config = json.load(file)

# Get the hue bridge ip
if not config['hue']['bridge_ip']:
    # TODO: get user input here
    print "blah"

# Check for an existing hue user
if not config['hue']['bridge_user']:
    # One doesn't exist, let's create one
    print "No Hue user exists, creating new one..."
    config['hue']['bridge_user'] = create_new_username(config['hue']['bridge_ip'])

    print "Saving updated config file"
    config_json = json.dumps(config, indent=4)
    f = open(config_filename, 'w')
    print >> f, config_json
    f.close()

print "User created and saved, flashing lights!"
# Get bridge
bridge = Bridge(config['hue_bridge_ip'], config['hue_bridge_user'])
bridge.groups[0].action(alert='select')