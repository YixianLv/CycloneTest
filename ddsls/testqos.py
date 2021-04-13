from cyclonedds.core import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.topic import Topic
from pycdr import cdr
import time


@cdr
class hello:
    x: int


# sample = "hi"
# qos = Qos(Policy.Userdata(data=sample))
qos = Qos(Policy.OwnershipStrength(10))

domain_participant = DomainParticipant(0)
topic = Topic(domain_participant, "hello", hello)
publisher = Publisher(domain_participant)
writer = DataWriter(publisher, topic, qos=qos)
print(qos)
time.sleep(5)

# sample = int(input("input new user data: "))
# qos = Qos(Policy.Userdata(data=sample))
qos = Qos(Policy.OwnershipStrength(20))

writer.set_qos(qos)
print(qos)
time.sleep(20)
