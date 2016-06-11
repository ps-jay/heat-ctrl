# Prep

Because Docker containers run in their own private network space, uPnP is not going to work from within a container to discover a Wemo switch outside of the containers.

So we need to prepare some ~/.wemo/ files outside of the container:

```
virtualenv <venv>
source <venv>/bin/activate
pip install ouimeaux  ## version 0.7.9.post0 works for me
wemo -v -d -b <lan_interface>:<any_ephemeral_port> list
rsync -HPvax --delete ~/.wemo/ <heatctrl_gitroot>/.wemo/
```

# Building / Running

```
docker build -t local/heat-ctrl .
docker run -it -d -m 128m --restart=always --name heat-ctrl local/heat-ctrl  ## yup, -it is needed
```

# Notes

* Static IP address for the Wemo switches is mandatory (usually by DHCP allocation)
* Wemo .cache is burned into the Docker image, so a new image will be required if switches are added/removed/updated

# Todo

* Unittests
* Externalise configuration
