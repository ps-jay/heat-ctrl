FROM python:2

MAINTAINER Philip Jay <phil@jay.id.au>

ENV TZ Australia/Melbourne

RUN pip install --upgrade \
      pip \
      astral \
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

CMD [ "python", "/opt/heat-ctrl/heat_ctrl.py" ]
