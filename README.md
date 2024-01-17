# Link2Home Powerplugs integration for Home-Assistant

![HassFest tests](https://github.com/renenulschde/ha_link2home/workflows/Validate%20with%20hassfest/badge.svg)

> :warning: This component is in an very early state and tested with an Link2Home D2 outdoor powerplug only.

## Features:

- Connect to Link2Home Cloud and collect registered devices
- Find registered devices in your local network
- Create sensors and switches for the found devices

## Installation

### Manual installation

- This is a Home Assistant custom component (not an Add-in).
- Download the folder custom_component and copy it into your Home-Assistant config folder.
- [How to install a custom component?](https://www.google.com/search?q=how+to+install+custom+components+home+assistant)
- Restart HA, Refresh your HA Browser window

### HACS

- Add a custom repository - [more here](https://hacs.xyz/docs/faq/custom_repositories/)
  - URL: https://github.com/ReneNulschDE/ha_link2home
  - Type: Integration
- Restart HA, Refresh your HA Browser window

## Configuration

Use the "Add Integration" in Home Assistant and select "Link2Home" and follow the following steps:

1. Put in your Link2Home email address and password in the component setup.
2. For some environments like Ubuntu the udp broadcasting function must be enabled (PERM Error 13 on component load)
   - collect old value: `sysctl net.ipv4.ping_group_range`
   - set new value: `sudo sysctl -w net.ipv4.ping_group_range="0 65535"`
   - Note: Unsecure config, check the group id of your HA-user and adjust the values. (`getent group YOUR_USER`, example: `="1000 1000"`)

## Sensors

Todo: Add doc

## Switches

Switches are created for each channel.
Todo: Add doc

## Logging

Set the logging to debug with the following settings in case of problems.

```
logger:
  default: warn
  logs:
    custom_components.ha_link2home: debug
```

## Thanks

Based on the repos:

- https://github.com/TA2k/ioBroker.link2home
- https://github.com/oxygen0211/ha-link2home

## Trademark Legal Notices

All product names, trademarks and registered trademarks in the images in this
repository, are property of their respective owners. All images in this
repository are used by this project for identification purposes
only.

The use of these names, trademarks and brands appearing in these image files,
do not imply endorsement.
