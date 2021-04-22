#!/usr/bin/env python3
import sys
import json
import argparse
from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import (BuiltinDataReader, BuiltinTopicDcpsParticipant,
                                BuiltinTopicDcpsSubscription,  BuiltinTopicDcpsPublication)
from cyclonedds.util import duration
from cyclonedds.core import WaitSet, ReadCondition, ViewState, InstanceState, SampleState


class TopicManager:
    def __init__(self, reader, topic_type, args):
        self.reader = reader
        self.topic_type = topic_type
        self.console_print = not args.filename
        self.enable_json = args.json
        self.enable_view = args.verbose
        self.tracked_entities = {}
        self.qoses = {}
        self.strings = ""
        self.read_cond = ReadCondition(reader, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        self.disposed_cond = ReadCondition(reader, ViewState.Any | InstanceState.NotAliveDisposed | SampleState.Any)

    def poll(self):
        samples = self.reader.take(N=100, condition=self.read_cond)
        disposed_samples = self.reader.take(N=100, condition=self.disposed_cond)
        if len(samples):
            print("\n--- New", self.topic_type, "------------", end="", flush=True)
            self.manage_samples(samples)
            self.check_qos_changes(samples)
        if len(disposed_samples):
            print("\n--- Disposed", self.topic_type, "------------", end="", flush=True)
            self.manage_samples(disposed_samples)

        if self.console_print and self.tracked_entities and (samples or disposed_samples):
            Output.to_console(self)

    def manage_samples(self, samples):
        for sample in samples:
            if self.topic_type == "PARTICIPANT":
                self.tracked_entities = {
                    self.topic_type: {
                        "key": str(sample.key)
                        }
                    }
            elif ((self.topic_type == "SUBSCRIPTION" and sample.key == self.reader.get_guid())
                  or self.topic_type == "PUBLICATION"):
                self.tracked_entities = {
                    self.topic_type: {
                        "key": str(sample.key),
                        "participant_key": str(sample.participant_key),
                        "topic_name": sample.topic_name,
                        "qos": sample.qos.asdict()
                        }
                    }

    def check_qos_changes(self, samples):
        for sample in samples:
            key = sample.key
            if self.qoses.get(key, 0) == 0:
                self.qoses[key] = sample.qos
            elif self.qoses[key] != sample.qos:
                for i in self.qoses[key]:
                    if (self.qoses[key][i] != sample.qos[i]):
                        print("\n\033[1mQos changed:\033[0m\nfor the", self.topic_type, "of topic '",
                              sample.topic_name, "'", "\nwith key =", sample.key, ":\n ",
                              "\033[1m", str(self.qoses[key][i]), "->", str(sample.qos[i]), "\033[0m")
                self.qoses[key] = sample.qos
                if not self.enable_view and self.console_print:
                    self.tracked_entities = 0

    def add_to_waitset(self, waitset):
        waitset.attach(self.read_cond)
        waitset.attach(self.disposed_cond)


class Output:
    def to_file(self, fp):
        for i in range(len(self)):
            if self[i].tracked_entities:
                if self[i].enable_json:
                    json.dump(self[i].tracked_entities, fp, indent=4)
                else:
                    Output.in_strings(self[i])
                    fp.write(str(self[i].strings))

    def to_console(self):
        if self.enable_json:
            json.dump(self.tracked_entities, sys.stdout, indent=4)
        else:
            Output.in_strings(self)
            print(self.strings)

    def in_strings(self):
        for topic, data in self.tracked_entities.items():
            self.strings = "\n" + topic
            for name, value in data.items():
                if name == "qos":
                    self.strings += "\n " + name + ":"
                    for i in value.items():
                        self.strings += "\n  " + str(i)
                else:
                    self.strings += "\n " + name + ":" + value


class parse_args:
    def __init__(self, args):
        if args.topic:
            if args.topic == "dcpsparticipant":
                self.topic = [["PARTICIPANT", BuiltinTopicDcpsParticipant]]
            elif args.topic == "dcpssubscription":
                self.topic = [["SUBSCRIPTION", BuiltinTopicDcpsSubscription]]
            else:
                self.topic = [["PUBLICATION", BuiltinTopicDcpsPublication]]

        if args.all is True:
            self.topic = [["PARTICIPANT", BuiltinTopicDcpsParticipant],
                          ["SUBSCRIPTION", BuiltinTopicDcpsSubscription],
                          ["PUBLICATION", BuiltinTopicDcpsPublication]]


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, help="Define the domain participant id", default=0)
    parser.add_argument("-f", "--filename", type=str, help="Write to file")
    parser.add_argument("-j", "--json", action="store_true", help="Print output in JSON format")
    parser.add_argument("-w", "--watch", action="store_true", help="Watch for data reader & writer & qoses changes")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="View the sample when Qos changes (available in --watch mode")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", "--all", action="store_true", help="for all topics")
    group.add_argument("-t", "--topic", choices=["dcpsparticipant", "dcpssubscription", "dcpspublication"],
                       help="for one specific topic")
    args = parser.parse_args()
    return args


def main():
    manager = []
    args = create_parser()
    dp = DomainParticipant(args.id)
    topics = parse_args(args)
    waitset = WaitSet(dp)

    for type, topic in topics.topic:
        manager.append(TopicManager(BuiltinDataReader(dp, topic), type, args))
        manager[-1].add_to_waitset(waitset)
    if args.watch:
        try:
            while True:
                for i in range(len(manager)):
                    waitset.wait(duration(milliseconds=20))
                    manager[i].poll()
        except KeyboardInterrupt:
            pass
    else:
        for i in range(len(manager)):
            manager[i].poll()

    if args.filename:
        try:
            with open(args.filename, 'w') as f:
                Output.to_file(manager, f)
                print("\nResults have been written to file", args.filename, "\n")
        except OSError:
            print("could not open file")
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
