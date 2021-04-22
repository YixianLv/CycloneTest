from cyclonedds.core import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.topic import Topic
from pycdr import cdr

import time


@cdr
class hello:
    x: int


def change_qos(qos):
    writer.set_qos(qos)
    print(qos.asdict())


sample = "hi"
qos = Qos(
            Policy.Userdata(data=sample.encode()),
            Policy.OwnershipStrength(10)
         )

domain_participant = DomainParticipant(0)
topic = Topic(domain_participant, "hello", hello)
publisher = Publisher(domain_participant)
writer = DataWriter(publisher, topic, qos=qos)
print(qos.asdict())
time.sleep(3)

qos = Qos(Policy.OwnershipStrength(20))
change_qos(qos)

sample = input("input new user data: ")
qos = Qos(Policy.Userdata(data=sample.encode()))
change_qos(qos)
time.sleep(5)
