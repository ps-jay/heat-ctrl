FROM python:2

MAINTAINER Philip Jay <phil@jay.id.au>

ENV TZ Australia/Melbourne

RUN pip install --upgrade \
      pip \
      astral \
      ouimeaux \
      pylint \
      requests \
 && rm -rf /root/.cache/

ADD pylint.conf /root/pylint.conf

RUN mkdir /opt/heat-ctrl/
ADD *.py /opt/heat-ctrl/

RUN pylint \
      --persistent=n \
      --rcfile=/root/pylint.conf \
      /opt/heat-ctrl/*.py

RUN useradd -m -r heat-ctrl

ADD .wemo/ /home/heat-ctrl/.wemo/

RUN chown -R heat-ctrl:heat-ctrl \
      /home/heat-ctrl \
      /opt/heat-ctrl

USER heat-ctrl

CMD [ "python", "/opt/heat-ctrl/heat_ctrl.py" ]
