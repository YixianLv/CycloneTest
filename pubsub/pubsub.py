#!/usr/bin/env python3
import sys
import select
import argparse
import re
from dataclasses import fields
from datastruct import Integer, String
from util import qos_help
from cyclonedds.core import WaitSet, ReadCondition, ViewState, InstanceState, SampleState
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic
from cyclonedds.util import duration
from cyclonedds.qos import Qos, Policy


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


class Qosmanager(Topicmanger):
    def __init__(self):
        self.parse_qos = re.compile(r"^([\w\d\-\.]+)(\([\w\d\.\-]+(?:,[\w\d\.\-]+)*\))?$")

    def construct_policy(self, txt):
        m = self.parse_qos.match(txt)
        if not m:
            raise Exception(f"Invalid format for qos '{txt}'")

        policy_name = m.group(1)

        if not policy_name.startswith("Policy."):
            policy_name = f"Policy.{policy_name}"

        if not policy_name in Qos._policy_mapper:
            raise Exception(f"Unknown qos policy {policy_name}")

        policy = Qos._policy_mapper[policy_name]
        _fields = fields(policy)

        if len(_fields) == 0 and m.group(2) is None:
            # No arguments needed and none provided
            return policy
        elif len(_fields) == 0:
            # No arguments needed but are provided
            raise Exception(f"{policy_name} requires no arguments but some were provided.")
        elif m.group(2) is None:
            # Arguments needed but none provided
            raise Exception(f"{policy_name} requires arguments but none were provided.")

        # Trim of outer parenthesis and split
        args = m.group(2).strip("()").split(',')

        if len(args) != len(_fields):
            raise Exception(f"{policy_name} requires {len(_fields)} arguments but {len(args)} were provided.")

        # convert to correct types
        try:
            args = [field.type(arg) for field, arg in zip(_fields, args)]
        except ValueError as e:
            raise Exception(f"Incorrect type provided for an argument, {e}")
        return policy(*args)


def create_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-T", "--topic", type=str, required=True, help="The name of the topic to publish/subscribe to")
    parser.add_argument("-q", "--qos", help="Set QoS for entities, check '--qoshelp' for available QoS and usage")
    parser.add_argument("--qoshelp", action="store_true", help="Avaialbe QoS and usage are:\n" + "\n".join(map(str, qos_help())))
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
    args = parser.parse_args()
    return args


def main():
    policies = Qos._policy_mapper
    qos_manager = Qosmanager()
    qos = None
    args = create_parser()
    if args.qos:
        qos = qos_manager.construct_policy(args.qos)

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
