import time
import string
import random
import datetime

from cdds.core import Qos, Policy
from cdds.domain import DomainParticipant
from cdds.topic import Topic
from cdds.pub import Publisher, DataWriter
from cdds.util import duration
from tempsensor import TempSensor, TemperatureScale

qos = Qos(
    Policy.Reliability.Reliable(duration(seconds=1)),
    Policy.Deadline(duration(microseconds=10)),
    Policy.History.KeepLast(5),
    Policy.Durability.Persistent
)

participant = DomainParticipant(0)
topic = Topic(participant, 'TempSensorTopic', TempSensor, qos = qos)
publisher = Publisher(participant)
writer = DataWriter(publisher, topic)

id = 1
scale = TemperatureScale.CELSIUS

while True:
    temp = 25 + random.uniform(-8, 8)
    hum = 0.5 + random.uniform(0, 0.2)
    time_stamp = datetime.datetime.now()
    sensor = TempSensor(id, temp, hum, scale.value, str(time_stamp))
    writer.write(sensor)
    print(sensor)
    time.sleep(1)