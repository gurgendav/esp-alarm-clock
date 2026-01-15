# Analogue Bedside Clock

This project builds an Analogue bedside clock out of a M5Stack Dial; the main purpose is to be able to set an alarm in Home Assistant by twisting the dial.

I have the alarm routine in Home Assistant slow fade up my bedsite lights, open the shutters, put on the air purifier and start the robot vacuum cleaners in the house.

You'll need:
- An M5Stack Dial: https://docs.m5stack.com/en/core/M5Dial
- Some 3D printed parts: 

# Installing esphome & compiling this project on a Mac
```sh
# We'll use pipx to install esphome, and brew to install pipx
$ brew install pipx libmagic cairo

# Install esphome in its own virtual env
$ pipx install esphome

# Add some dependencies to the virtual env
$ pipx runpip esphome install python-magic pillow==11.3.0 cairosvg

# Install the wind tunnel (first time - your device name will vary)
$ ~/.local/bin/esphome run --device=/dev/tty.usbmodem31301 clock.yaml

# Install the wind tunnel (susequent times, via WiFi)
$ ~/.local/bin/esphome run clock.yaml
```