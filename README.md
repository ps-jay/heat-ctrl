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
