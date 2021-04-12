import time
import random
import argparse
import threading

from cyclonedds.core import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.topic import Topic
from cyclonedds.util import duration

from vehicles import Vehicle


def print_cart(cart, writer, message):
    while True:
        cart.x += random.choice([-1, 0, 1])
        cart.y += random.choice([-1, 0, 1])
        writer.write(cart)
        print(message)
        time.sleep(random.random() * 0.9 + 0.1)

class KeyboardThread(threading.Thread):

    def __init__(self, input_cbk=None, name='keyboard-input-thread'):
        self.input_cbk = input_cbk
        super(KeyboardThread, self).__init__(name=name)
        self.start()

    def run(self):
        while True:
            self.input_cbk(input())


def set_qos(key):
    if key == "a":
        qos = Qos(Policy.Durability.TransientLocal)
        writer = DataWriter(publisher, topic, qos=qos)
        print_cart(cart, writer, ">> Wrote vehicle in new qos")
    else:
        pass


qos = Qos(
            Policy.Reliability.BestEffort(duration(seconds=1)),
            Policy.Deadline(duration(microseconds=10)),
            Policy.Durability.Transient,
            Policy.History.KeepLast(10)
        )

domain_participant = DomainParticipant(0)
topic = Topic(domain_participant, 'Vehicle', Vehicle)
publisher = Publisher(domain_participant)
writer = DataWriter(publisher, topic, qos=qos)

KeyboardThread(set_qos)

cart = Vehicle(name="Dallara IL-15", x=200, y=200)

print_cart(cart, writer, ">> Wrote vehicle")
