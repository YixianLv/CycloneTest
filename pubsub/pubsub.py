#!/usr/bin/env python3
import sys
import select
import argparse
import re
import json
from dataclasses import fields
from datastruct import Integer, String, IntArray, StrArray, IntSequence, StrSequence
from util import qos_help_msg, QosMapper, default_qos_val
from cyclonedds.core import Listener, DDSException, WaitSet, ReadCondition, ViewState, InstanceState, SampleState
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.topic import Topic
from cyclonedds.util import duration
from cyclonedds.qos import Qos


class QosListener(Listener):
    def on_requested_incompatible_qos(self, reader, status):
        print("WARNING: The Qos requested by the reader is incompatible to the Qos offered by the writer. " +
              "PubSub may not be available.")


class Topicmanger():
    def __init__(self, args, dp, qos, waitset):
        self.dp = dp
        self.topic_name = args.topic
        self.seq = -1
        self.tqos, self.pqos, self.sqos, self.wqos, self.rqos = qos
        self.reader = []
        try:
            self.listener = QosListener()
            self.pub = Publisher(dp, qos=self.pqos)
            self.sub = Subscriber(dp, qos=self.sqos)
            self.int_writer = self.create_entities("int", Integer)
            self.str_writer = self.create_entities("str", String)
            self.int_array_writer = self.create_entities("int_array", IntArray)
            self.str_array_writer = self.create_entities("str_array", StrArray)
            self.int_seq_writer = self.create_entities("int_seq", IntSequence)
            self.str_seq_writer = self.create_entities("str_seq", StrSequence)
        except DDSException:
            raise SystemExit("Error: The arguments inputted are considered invalid for cyclonedds.")

        self.read_cond = ReadCondition(self.reader[0], ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(self.read_cond)

    def write(self, input):
        self.seq += 1
        if type(input) is int:
            self.int_writer.write(Integer(self.seq, input))
        elif type(input) is list:
            for i in input:
                if not isinstance(i, type(input[0])):
                    raise Exception("TypeError: Element type inconsistent, " +
                                    "input list should be a list of integer or a list of string.")

            # Write array or sequence of integer
            if isinstance(input[0], int):
                int_arr_len = IntArray.__annotations__['keyval'].__metadata__[0].length
                if len(input) == int_arr_len:
                    self.int_array_writer.write(IntArray(self.seq, input))
                else:
                    self.int_seq_writer.write(IntSequence(self.seq, input))
            # Write array or sequence of string
            else:
                str_arr_len = StrArray.__annotations__['keyval'].__metadata__[0].length
                if len(input) == str_arr_len:
                    self.str_array_writer.write(StrArray(self.seq, input))
                else:
                    self.str_seq_writer.write(StrSequence(self.seq, input))
        else:
            self.str_writer.write(String(self.seq, input))

    def read(self):
        for reader in self.reader:
            for sample in reader.take(N=100):
                print(f"Subscriberd: {sample}")

    def create_entities(self, name, datastruct):
        topic = Topic(self.dp, self.topic_name + name, datastruct, qos=self.tqos)
        writer = DataWriter(self.pub, topic, qos=self.wqos)
        if name == "int":
            self.reader.append(DataReader(self.sub, topic, qos=self.rqos, listener=self.listener))
        else:
            self.reader.append(DataReader(self.sub, topic, qos=self.rqos))
        return writer


class Qosmanager():
    def __init__(self):
        self.parse_qos = re.compile(r"^([\w\d\-\.]+)?(\s[\w\d\.\-]+(?:,\s[\w\d\.\-]+)*)?$")
        self.special_qos = ["Partition", "DurabilityService", "WriterDataLifecycle",
                            "Userdata", "Groupdata", "Topicdata", "PresentationAccessScope.Instance",
                            "PresentationAccessScope.Topic", "PresentationAccessScope.Group"]
        self.special_scope = self.special_qos[:6] + ["PresentationAccessScope"]
        self.policy_name = None
        self.tqos, self.pqos, self.sqos, self.wqos, self.rqos = None, None, None, None, None

    def construct_policy(self, txt):
        for sp in self.special_qos:
            if re.search(sp, txt):
                self.policy_name = sp
        m = self.parse_qos.match(txt)
        if not m and not self.policy_name:
            raise Exception(f"Invalid format for qos '{txt}'")
        if m:
            self.policy_name = m.group(1)

        if not self.policy_name.startswith("Policy."):
            self.policy_name = f"Policy.{self.policy_name}"

        if self.policy_name not in Qos._policy_mapper:
            raise Exception(f"Unknown qos policy {self.policy_name}")

        policy = Qos._policy_mapper[self.policy_name]
        _fields = fields(policy)

        if policy.__scope__ in self.special_scope:
            return self.special_policy(policy, _fields, m, txt)

        else:
            # Check if the numbers of provided arguments meets the required numbers
            if len(_fields) == 0 and m.group(2) is None:
                return policy
            elif len(_fields) == 0:
                raise Exception(f"{self.policy_name} requires no arguments but some were provided.")
            elif m.group(2) is None:  # When user didn't define the values for the policy, use default value
                args = default_qos_val[self.policy_name]

            # Trim of outer parenthesis and split
            if m.group(2):
                args = m.group(2).strip().split(', ')
                if len(args) != len(_fields):
                    raise Exception(f"{self.policy_name} requires {len(_fields)} arguments but {len(args)} were provided.")

                # convert to correct types
                try:
                    args = [field.type(arg) for field, arg in zip(_fields, args)]
                except ValueError as e:
                    raise Exception(f"Incorrect type provided for an argument, {e}")
            return policy(*args)

    def special_policy(self, policy, fields, match, txt):
        # Seq[str]
        if policy.__scope__ == "Partition":
            sp_qos = re.compile(r"^([\w\d\-\.]+)?(\s)?(\s(\[[\w\d\.\-]+(?:,\s[\w\d\.\-]+)*\]))?$")
            m = sp_qos.match(txt)
            if not m:
                raise Exception(f"Invalid format for qos '{txt}'")

            if m.group(3) is None:
                args = default_qos_val[self.policy_name]
            else:
                args = m.group(3).strip("[]").split(', ')
            return policy(args)

        # Subpolicy with History
        elif policy.__scope__ == "DurabilityService":
            sp_qos = re.compile(r"^([\w\d\-\.]+)?(\s([\w\d\.\-]+),\s([\w\d\-\.\s]+)([,\s\w\d\.\-]+)*)?$")
            m = sp_qos.match(txt)
            if not m:
                raise Exception(f"Invalid format for qos '{txt}'")

            if m.group(2) is None:
                args = default_qos_val[self.policy_name]
            else:
                input_args = []
                input_args.append(m.group(3).strip(" ").split(", "))
                input_args.append(m.group(4).strip(" ").split(" "))
                for val in m.group(5).strip(", ").split(", "):
                    input_args.append([val])
                if len(input_args) != len(fields):
                    raise Exception(
                        f"{policy.__scope__} requires {len(fields)} arguments but {len(input_args)} were provided.")

                args = []
                # Check all the arguments except the History subpolicy
                for field, arg in zip(fields, input_args):
                    if field.type is int:
                        try:
                            args.append(field.type(arg[0]))
                        except ValueError as e:
                            raise Exception(f"Incorrect type provided for an argument, {e}")

                # Check the History subpolicy
                if not input_args[1][0].startswith("Policy."):
                    input_args[1][0] = f"Policy.{input_args[1][0]}"
                if input_args[1][0] == "Policy.History.KeepLast" and (int(input_args[1][1])):
                    hist_policy = [Qos._policy_mapper["Policy.History.KeepLast"](int(input_args[1][1]))]
                elif input_args[1][0] == "Policy.History.KeepAll":
                    hist_policy = [Qos._policy_mapper["Policy.History.KeepAll"]]
                else:
                    raise Exception(f"Invalid format or argument for Policy.History '{input_args[1]}'")

                args = args[:1] + hist_policy + args[1:]
            return policy(*args)

        # Bool
        elif policy.__scope__ in ["PresentationAccessScope", "WriterDataLifecycle"]:
            if match.group(2) is None:
                args = default_qos_val[self.policy_name]
            else:
                args = match.group(2).strip().split(', ')
                args = [json.loads(arg.lower()) for field, arg in zip(fields, args)]
            return policy(*args)

        # Bytes --Userdata/Topicdata/Groupdata
        else:
            if match.group(2) is None:
                args = default_qos_val[self.policy_name]
            else:
                args = []
                for arg in match.group(2).strip().split(' '):
                    args.append(arg.encode())
            return policy(*args)

    def entity_qos(self, qos, entity):
        if entity == "t":
            self.tqos = self.check_entity_qos("topic", QosMapper.topic, qos)
        elif entity == "p":
            self.pqos = self.check_entity_qos("publisher", QosMapper.pubsub, qos)
        elif entity == "s":
            self.sqos = self.check_entity_qos("subscriber", QosMapper.pubsub, qos)
        elif entity == "w":
            self.wqos = self.check_entity_qos("writer", QosMapper.writer, qos)
        elif entity == "r":
            self.rqos = self.check_entity_qos("reader", QosMapper.reader, qos)
        else:
            for e in ["t", "p", "s", "w", "r"]:
                self.entity_qos(qos, e)
        return [self.tqos, self.pqos, self.sqos, self.wqos, self.rqos]

    def check_entity_qos(self, e, eqos_mapper, qos):
        if self.policy_name in eqos_mapper:
            eqos = qos
            return eqos
        else:
            print(f"The {self.policy_name} is not applicable for {e}, will be ignored.")


def create_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-T", "--topic", type=str, help="The name of the topic to publish/subscribe to")
    parser.add_argument("-e", "--entity", choices=["a", "t", "p", "s", "w", "r"], help='''Select the entites to set the qos.
Choose between a(all) entities, t(topic), p(publisher), s(subscriber), w(writer) and r(reader). (default: a).
Inapplicable qos will be ignored.''')
    parser.add_argument("-q", "--qos", nargs="+", action='append',
                        help="Set QoS for entities, check '--qoshelp' for available QoS and usage\n")
    group.add_argument("--qoshelp", action="store_true", help=qos_help_msg)
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
    args = parser.parse_args()
    if args.qoshelp:
        print(qos_help_msg)
        sys.exit(0)
    if args.entity and not args.qos:
        raise SystemExit("Error: The following argument is required: -q/--qos")
    return args


def main():
    qos_manager = Qosmanager()
    qos = None
    policy = []
    args = create_parser()
    entities_qos = [None] * 5
    if args.qos:
        for q in args.qos:
            myqos = ' '.join(q)
            policy.append(qos_manager.construct_policy(myqos))
            qos = Qos(*policy)
            entities_qos = qos_manager.entity_qos(qos, args.entity)

    dp = DomainParticipant(0)
    waitset = WaitSet(dp)
    manager = Topicmanger(args, dp, entities_qos, waitset)
    if args.topic:
        try:
            while True:
                input = select.select([sys.stdin], [], [], 0)[0]
                if input:
                    for text in sys.stdin.readline().split():
                        try:
                            text = eval(text)
                            manager.write(text)
                        except NameError:
                            manager.write(text.rstrip("\n"))
                manager.read()
                waitset.wait(duration(microseconds=20))
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
