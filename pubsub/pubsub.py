#!/usr/bin/env python3
import sys
import select
import argparse
from datastruct import Integer, String
from cyclonedds.core import WaitSet, ReadCondition, ViewState, InstanceState, SampleState
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic
from cyclonedds.util import duration
from cyclonedds.qos import Qos
from dataclasses import fields


class Topicmanger:
    def __init__(self, args, dp, qos, waitset):
        self.topic_name = args.topic
        self.seq = -1
        int_topic = Topic(dp, self.topic_name + "int", Integer, qos=qos)
        str_topic = Topic(dp, self.topic_name, String, qos=qos)
        self.int_writer = DataWriter(dp, int_topic, qos=qos)
        self.int_reader = DataReader(dp, int_topic, qos=qos)
        self.str_writer = DataWriter(dp, str_topic, qos=qos)
        self.str_reader = DataReader(dp, str_topic, qos=qos)
        self.read_cond = ReadCondition(self.int_reader, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(self.read_cond)

    def write(self, input):
        self.seq += 1
        if type(input) is int:
            msg = Integer(self.seq, input)
            self.int_writer.write(msg)
        else:
            msg = String(self.seq, input)
            self.str_writer.write(msg)

    def read(self):
        for sample in self.int_reader.take(N=100):
            print("Subscribed:", sample)
        for sample in self.str_reader.take(N=100):
            print("Subscribed:", sample)
            # print("Subscribed: {seq =", sample.seq, ", keyval =", sample.keyval, "}")


def qos_fields(policies, args):
    qos = 0
    if len(args.qos) == 1:
        qos = Qos(policies[args.qos[0]])
    elif len(args.qos) > 1:
        try:
            if len(args.qos) - 1 != len(fields(policies[args.qos[0]])):
                print(f"Error! The numbers of variables needed for the qos is {len(fields(policies[args.qos[0]]))}, "
                      f"but {len(args.qos) - 1} variables was inputted.")
                for field in fields(policies[args.qos[0]]):
                    print(f"  {field.name} {field.type}")
                sys.exit(1)
            else:
                qos = Qos(policies[args.qos[0]](args.qos[1:]))
                print(args.qos[1:])

        except KeyError:
            print("Qos incorrect: Select a Qos from the Qos list, eg.Policy.History.KeepAll, Policy.History.KeepLast 10")
            sys.exit(1)
    return qos


def create_parser(policies):
    parser = argparse.ArgumentParser()
    parser.add_argument("-T", "--topic", type=str, required=True, help="The name of the topic to publish/subscribe to")
    parser.add_argument("-q", "--qos", nargs="*", help=f'''Customize the qos for the entities, eg.Policy.History.KeepAll, Policy.History.KeepLast 10\n
                        Available qos are: {policies.keys()}''')
    args = parser.parse_args()
    return args


def main():
    policies = Qos._policy_mapper
    args = create_parser(policies)
    qos = qos_fields(policies, args)

    dp = DomainParticipant(0)
    waitset = WaitSet(dp)
    manager = Topicmanger(args, dp, qos, waitset)
    if args.topic:
        try:
            while True:
                input = select.select([sys.stdin], [], [], 0)[0]
                if input:
                    for text in sys.stdin.readline().split():
                        try:
                            text = int(text)
                            manager.write(text)
                        except ValueError:
                            manager.write(text.rstrip("\n"))
                manager.read()
                waitset.wait(duration(microseconds=20))
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
