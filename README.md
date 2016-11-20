# PiZeroDoorbell

## Summary

This is a project designed to run on a Raspberry Pi and use an Amazon Dash button as a doorbell. The doorbell noise plays through a Sonos and any other players in it's current group and then restarts the previously playing music.

## Background

There are lots and bits of pieces of code around the place for setting up this project, but none of them really fit the bill for me. The better ones still didn't work as well as I would like - so I wrote my own. I'm still a python beginner and this is my first Raspberry Pi so hey - why not. I tried to make it easy for me to keep running and hopefully easy for people to slot into their environments through the use of basic config files. This way it is easy for me to fix things it I want to change which Sonos to use for alerting or change the MAC of the Amazon Dash button when the first inevitably dies.

The main thing I have done is to split the normal process into two parts. I found it very slow to query for the current state of the Sonos player, save it, play the sound, reset the Sonos state. This seemed to add a couple of seconds before the doorbell sound played **on top** of the couple of seconds it takes for the Dash button to trigger the process. To counter this I wrote a script which just polls the Sonos environment on the local network at a fixed interval (30 seconds by default but easily configurable) and saves the state. Then when the doorbell is triggered it only needs to read the state file and do some basic maths to work out where to restart the music on the player.

## Feature overview

- Quick response time to button push
- Resumes the music on Sonos player after playing sound
- Sets volume to customizable value for doorbell then resets to original value
- Works with radio streams, TV and Sonos queues/playlists
- Easily customisable through basic configuration file
- Sends email alerts when visitors arrive
- Flashes Hue lights

## Upcoming features

- Attach photo to email or link to a live video stream (requires Raspberry Pi Camera)
- Triggered by Bluetooth button instead of Amazon Dash
- Allow multiple Sonos players to be defined for doorbell sound playback

## Installation instructions

**These instructions are written for a Raspberry Pi beginner (as I am). Feel free to skip bits you don't need  **

### Change your Raspberry Pi password

If you haven't already done this - you should have. Do it now.

`sudo raspi-config`

Choose the "change_pass" option

### Enable camera (if installed, functionality not yet implemented)

`sudo raspi-config`

Choose the 'camera' option and Enable, then reboot your Pi as follows:

`sudo shutdown -r now`

**Remember to log in with your new password if you just changed it!**

### Get your Raspberry Pi updated

These two commands make take a while to run

```
sudo apt-get update
sudo apt-get upgrade
```
### Install the packages we need 

#### [SoCo](http://python-soco.com/) (Required to play sound through Sonos)

`sudo pip install soco`

#### [Qhue](https://github.com/quentinsf/qhue) (Used for alerting using Hue lights)

`sudo pip install qhue`

#### [scapy](http://www.secdev.org/projects/scapy/) (Used for working out when Amazon Dash button is pressed)

`sudo apt-get install python-scapy tcpdump`

#### lighttd (Used to host the doorbell sound file

If you want to host your doorbell sound file in your local network then you need to follow these steps. You can alternatively use a link to an mp3 hosted anywhere on the internet, but bear in mind your doorbell will not work without an working internet connection in that case.

```
sudo apt-get -y install lighttpd
sudo chown www-data:www-data /var/www
sudo chmod 775 /var/www
sudo usermod -a -G www-data pi
```

I would also recommend setting a DHCP reservation for your Raspbery Pi on your router if you choose to host your file locally like this.

### Find your doorbell sounds

If you want to use something on the internet - then find a direct link to a hosted mp3 and copy it for later
If you want to host it locally:

- Find the sound file of your choice and download it
- SCP it to your Raspberry Pi
  - On Linux/OSX - scp ./path/to/doorbell.mp3 pi@<raspberry_pi_ip>:/var/www/doorbell.mp3
  - On Windows - Download WinSCP

### Check out Doorbell code

```
cd ~ 
git clone https://github.com/mmmmmtasty/PiZeroDoorbell.git PiZeroDoorbell
```

### Adjust doorbell config

You need to know the MAC address of your dash button (get it from your router) and the name of the Sonos player you want to play the doorbell sound from

`nano ./PiZeroDoorbell/config/doorbell_config.json`

- Edit the ['amazon_dash']['mac_address'] to be the lower-cased MAC address of the Amazon Dash button.
- Edit the ['sonos']['doorbell_uri'] to be the URL to retrieve the doorbell mp3 file from
- Edit the ['sonos']['volume'] to be something sensible for the size of your house/location of your Sonos players
- If you require email, update the email settings with your easy-smtp.com login details (free to create an account)
- If you want to use your Hue lights for alerting, run:

`sudo python ./PiZeroDoorbell/hue_setup.py`

### Test to make sure both of the scripts involved run properly

```
sudo python ./PiZeroDoorbell/get_sonos_state.py &
sudo python ./PiZeroDoorbell/doorbell.py &
```

Wait a couple of minutes, try pressing the doorbell button and ensure that you don't have any exceptions at any point and that the doorbell rings.

### Make sure the doorbell starts when the Raspberry Pi boots

`sudo nano /etc/rc.local'

*Before* the `exit 0` line, add the following two lines:

```
sudo python ./PiZeroDoorbell/get_sonos_state.py &
sudo python ./PiZeroDoorbell/doorbell.py &
```

Hit Ctrl+o and hit Enter to save, then Ctrl+x to quit
Restart your Raspberry Pi and make sure it works




