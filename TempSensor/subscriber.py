import time
import string
import random
import datetime

from cdds.core import Listener, WaitSet, ReadCondition, QueryCondition, ViewState, SampleState, InstanceState, Qos, Policy
from cdds.domain import DomainParticipant
from cdds.topic import Topic
from cdds.sub import Subscriber, DataReader
from cdds.util import duration
from tempsensor import TempSensor, TemperatureScale
from cdds.internal.dds_types import SampleInfo

class MyListener(Listener):
    def on_data_available(self, reader):
        pass

    def on_liveliness_changed(self, reader, status):
        print(">> Liveliness event")


listener = MyListener()
qos = Qos(
    Policy.Reliability.Reliable(duration(seconds=1)),
    Policy.Deadline(duration(microseconds=10)),
    Policy.History.KeepLast(5),
    Policy.Durability.Persistent
)

participant = DomainParticipant(0)
topic = Topic(participant, 'TempSensorTopic', TempSensor, qos = qos)
subscriber = Subscriber(participant)
reader = DataReader(subscriber, topic, listener = listener)

condition = QueryCondition(reader, SampleState.NotRead | ViewState.Any | InstanceState.Alive, lambda vehicle: vehicle.x % 2 == 0)

waitset = WaitSet(participant)
waitset.attach(condition)

while True:
    waitset.wait(duration(seconds=1))
    reader.wait_for_historical_data(duration(seconds=10))
    samples = reader.read()
    if samples:
        for sample in samples:
            print(f"Read sample: Sensor(id={sample.id}, temp={sample.temp}, hum={sample.hum}, scale={sample.scale}, time={sample.time_stamp})")
    else:
        print("Waiting for sample")