#!/usr/bin/env python3
import sys
import select
import argparse
import re
import json
from dataclasses import fields
from datastruct import Integer, String
from util import qos_help_msg
from cyclonedds.core import WaitSet, ReadCondition, ViewState, InstanceState, SampleState
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic
from cyclonedds.util import duration
from cyclonedds.qos import Qos


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
        self.parse_qos = re.compile(r"^([\w\d\-\.]+)\s([\w\d\.\-]+(?:,\s[\w\d\.\-]+)*)?$")
        self.special_qos = ["Partition", "DurabilityService", "PresentationAccessScope.Instance",
                            "PresentationAccessScope.Topic", "PresentationAccessScope.Group",
                            "Userdata", "Groupdata", "Topicdata"]
        self.special_scope = ["Partition", "DurabilityService", "PresentationAccessScope",
                              "Userdata", "Groupdata", "Topicdata"]

    def construct_policy(self, txt):
        policy_name = None
        for sp in self.special_qos:
            if re.search(sp, txt):
                policy_name = sp
        m = self.parse_qos.match(txt)
        if not m and not policy_name:
            raise Exception(f"Invalid format for qos '{txt}'")
        if m:
            policy_name = m.group(1)

        if not policy_name.startswith("Policy."):
            policy_name = f"Policy.{policy_name}"

        if policy_name not in Qos._policy_mapper:
            raise Exception(f"Unknown qos policy {policy_name}")

        policy = Qos._policy_mapper[policy_name]
        _fields = fields(policy)

        if policy.__scope__ in self.special_scope:
            return self.special_policy(policy, _fields, m, txt)

        else:
            # Check if the numbers of provided arguments meets the required numbers
            if len(_fields) == 0 and m.group(2) is None:
                return policy
            elif len(_fields) == 0:
                raise Exception(f"{policy_name} requires no arguments but some were provided.")
            elif m.group(2) is None:
                raise Exception(f"{policy_name} requires arguments but none were provided.")

            # Trim of outer parenthesis and split
            args = m.group(2).strip().split(', ')
            if len(args) != len(_fields):
                raise Exception(f"{policy_name} requires {len(_fields)} arguments but {len(args)} were provided.")

            # convert to correct types
            try:
                args = [field.type(arg) for field, arg in zip(_fields, args)]
            except ValueError as e:
                raise Exception(f"Incorrect type provided for an argument, {e}")
            return policy(*args)

    def special_policy(self, policy, fields, match, txt):
        if policy.__scope__ == "Partition":  # seq[str]
            sp_qos = re.compile(r"^([\w\d\-\.]+)\s(\[[\w\d\.\-]+(?:,\s[\w\d\.\-]+)*\])?$")
            m = sp_qos.match(txt)
            if not m:
                raise Exception(f"Invalid format for qos '{txt}'")
            args = m.group(2).strip("[]").split(', ')
            return policy(args)

        elif policy.__scope__ == "DurabilityService":  # subpolicy with History
            sp_qos = re.compile(r"^([\w\d\-\.]+)\s([\w\d\.\-]+),\s(Policy.History.Keep[\w\d\-\.\s]+)([,\s\w\d\.\-]+)*?$")
            m = sp_qos.match(txt)
            if not m:
                raise Exception(f"Invalid format for qos '{txt}'")
            input_args = []
            input_args.append(m.group(2).strip(" ").split(", "))
            input_args.append(m.group(3).strip(" ").split(" "))
            for val in m.group(4).strip(", ").split(", "):
                input_args.append([val])
            if len(input_args) != len(fields):
                raise Exception(f"Policy.{policy.__scope__} requires {len(fields)} arguments but {len(input_args)} were provided.")

            args = []
            # Check all the arguments except the History subpolicy
            for field, arg in zip(fields, input_args):
                if field.type is int:
                    try:
                        args.append(field.type(arg[0]))
                    except ValueError as e:
                        raise Exception(f"Incorrect type provided for an argument, {e}")

            # Check the History subpolicy
            if input_args[1][0] == "Policy.History.KeepLast" and (int(input_args[1][1])):
                hist_policy = [Qos._policy_mapper["Policy.History.KeepLast"](int(input_args[1][1]))]
            elif input_args[1][0] == "Policy.History.KeepAll":
                hist_policy = [Qos._policy_mapper["Policy.History.KeepAll"]]
            else:
                raise Exception(f"Invalid format or argument for Policy.History '{input_args[1]}'")

            args = args[:1] + hist_policy + args[1:]
            print(f"args = {args}")
            return policy(*args)

        elif policy.__scope__ == "PresentationAccessScope":  # bool
            args = match.group(2).strip().split(', ')
            args = [json.loads(arg.lower()) for field, arg in zip(fields, args)]
            return policy(*args)

        else:  # bytes --Userdata/Topicdata/Groupdata
            args = []
            for arg in match.group(2).strip().split(' '):
                args.append(arg.encode())
            return policy(*args)


def create_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-T", "--topic", type=str, help="The name of the topic to publish/subscribe to")
    parser.add_argument("-q", "--qos", nargs="+", help="Set QoS for entities, check '--qoshelp' for available QoS and usage\n")
    group.add_argument("--qoshelp", action="store_true", help=qos_help_msg)
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
    args = parser.parse_args()
    if args.qoshelp:
        print(qos_help_msg)
        sys.exit(0)
    return args


def main():
    qos_manager = Qosmanager()
    qos = None
    args = create_parser()
    if args.qos:
        args.qos = ' '.join(args.qos)
        myqos = qos_manager.construct_policy(args.qos)
        qos = Qos(myqos)

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
