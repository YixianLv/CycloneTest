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
        self.enable_view = args.v
        self.tracked_entities = {}
        self.qoses = {}
        self.read_cond = ReadCondition(reader, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        self.disposed_cond = ReadCondition(reader, ViewState.Any | InstanceState.NotAliveDisposed | SampleState.Any)

    def poll(self):
        samples = self.reader.take(N=100, condition=self.read_cond)
        disposed_samples = self.reader.take(N=100, condition=self.disposed_cond)
        if len(samples) or len(disposed_samples):
            if len(samples):
                manage_samples(self, samples)
                check_qos_changes(self, samples)
            else:
                print("\n--- " + self.topic_type + " disposed ---")
                manage_samples(self, disposed_samples)

        if self.console_print and self.tracked_entities and samples:
            Output.to_console(self, self.tracked_entities)

    def add_to_waitset(self, waitset):
        waitset.attach(self.read_cond)
        waitset.attach(self.disposed_cond)


class Output(TopicManager):
    def to_file(self, fp):
        for i in range(len(self)):
            if self[i].tracked_entities:
                if self[i].enable_json:
                    json.dump(self[i].tracked_entities, fp, indent=4)
                else:
                    fp.write(str(self[i].tracked_entities))

    def to_console(self, obj):
        if self.enable_json:
            json.dump(obj, sys.stdout, indent=4)
        else:
            sys.stdout.write(str(obj))
            sys.stdout.flush()


class parse_args:
    def __init__(self, args, dp):
        if args.topic:
            if args.topic == "dcpsparticipant":
                self.topic = [["PARTICIPANT", BuiltinTopicDcpsParticipant]]
            elif args.topic == "dcpssubscription":
                self.topic = [["SUBSCRIPTION", BuiltinTopicDcpsSubscription]]
            else:
                self.topic = [["PUBLICATION", BuiltinTopicDcpsPublication]]

        if args.a is True:
            self.topic = [["PARTICIPANT", BuiltinTopicDcpsParticipant],
                          ["SUBSCRIPTION", BuiltinTopicDcpsSubscription],
                          ["PUBLICATION", BuiltinTopicDcpsPublication]]


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, help="Define the domain participant id", default=0)
    parser.add_argument("--filename", type=str, help="Write to file")
    parser.add_argument("--json", action="store_true", help="Print output in JSON format")
    parser.add_argument("--watch", action="store_true", help="Watch for data reader & writer & qoses changes")
    parser.add_argument("-v", action="store_true", help="View the sample when Qos changes (available in --watch mode")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", action="store_true", help="for all topics")
    group.add_argument("-t", "--topic", choices=["dcpsparticipant", "dcpssubscription", "dcpspublication"])
    args = parser.parse_args()
    return args


def manage_samples(obj, samples):
    for sample in samples:
        if obj.topic_type == "PARTICIPANT":
            obj.tracked_entities = {
                obj.topic_type: [{
                    "key": str(sample.key)
                    }]
                }
        elif ((obj.topic_type == "SUBSCRIPTION" and sample.key == obj.reader.get_guid())
              or obj.topic_type == "PUBLICATION"):
            obj.tracked_entities = {
                obj.topic_type: [{
                    "key": str(sample.key),
                    "participant_key": str(sample.participant_key),
                    "topic_name": sample.topic_name,
                    "qos": sample.qos.asdict()
                    }]
                }


def check_qos_changes(obj, samples):
    for sample in samples:
        key = sample.key
        if obj.qoses.get(key, 0) == 0:
            obj.qoses[key] = sample.qos
        elif obj.qoses[key] != sample.qos:
            for i in obj.qoses[key]:
                if (obj.qoses[key][i] != sample.qos[i]):
                    print("\n\033[1mQos changed for the", obj.topic_type, "of topic '", sample.topic_name, "' :\n ",
                          str(obj.qoses[key][i]), "->", str(sample.qos[i]), '\033[0m')
            obj.qoses[key] = sample.qos
            if not obj.enable_view and obj.console_print:
                obj.tracked_entities = 0


def main():
    manager = []
    args = create_parser()
    dp = DomainParticipant(args.id)
    topics = parse_args(args, dp)
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
        except OSError:
            print("could not open file")
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
