#!/usr/bin/env python3

import sys
import json
import argparse

from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import (BuiltinDataReader, BuiltinTopicDcpsParticipant,
                                BuiltinTopicDcpsSubscription,  BuiltinTopicDcpsPublication)
from cyclonedds.util import duration
from cyclonedds.core import WaitSet, ReadCondition, ViewState, InstanceState, SampleState


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, help="define the domain participant id", default=0)
    parser.add_argument("--filename", type=str, help="write to file")
    parser.add_argument("--json", action="store_true", help="print output in JSON format")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", action="store_true", help="for all topics")
    group.add_argument("-t", "--topics", choices=["dcpsparticipant", "dcpssubscription", "dcpspublication"])
    args = parser.parse_args()
    return args


def print_object(fp, obj, print_json):
    if print_json:
        json.dump(obj, fp, indent=4)
    else:
        fp.write(str(obj) + "\n")
        fp.flush()


result = []


def open_file(filename, obj, print_json, topic_type):
    if not filename:
        print_object(sys.stdout, obj, print_json)
    else:
        result.append(obj)
        with open(filename, mode="w") as fp:
            try:
                print_object(fp, result, print_json)
                print("Write to file " + filename)
                fp.close()
                return 0
            except Exception:
                return 1


def manage_samples(dr, samples, topic_type, filename, print_json):
    obj = []
    for sample in samples:
        if topic_type == "PARTICIPANT":
            sample = {
                topic_type: [{
                    "key": str(sample.key)
                }]
            }
            obj.append(sample)
        elif ((topic_type == "SUBSCRIPTION" and sample.key == dr.get_guid()) or
              topic_type == "PUBLICATION"):
            sample = {
                "topic_type": [{
                    "key": str(sample.key),
                    "participant_key": str(sample.participant_key),
                    "topic_name": sample.topic_name,
                    "qos": sample.qos.asdict()
                }]
            }
            # print(sample.get(topic_type))
            obj.append(sample)
    if len(obj):
        open_file(filename, obj, print_json, topic_type)


def manage_dcps_object(dp, dr, topic_type, filename, print_json):
    waitset = WaitSet(dp)
    condition = ReadCondition(dr, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
    disposed_cond = ReadCondition(dr, ViewState.Any | InstanceState.NotAliveDisposed | SampleState.Any)
    waitset.attach(condition)

    samples = dr.take(condition=condition)
    disposed_samples = dr.take(condition=disposed_cond)

    if len(samples) or len(disposed_samples):
        if len(samples):
            manage_samples(dr, samples, topic_type, filename, print_json)
        else:
            print("\n--- " + topic_type + " disposed ---")
            manage_samples(dr, disposed_samples, topic_type, filename, print_json)
    else:
        waitset.wait(duration(milliseconds=20))


def main():
    args = create_parser()
    dp = DomainParticipant(args.id)

    if args.topics:
        if args.topics == "dcpsparticipant":
            type = "PARTICIPANT"
            topic = BuiltinTopicDcpsParticipant
        elif args.topics == "dcpssubscription":
            type = "SUBSCRIPTION"
            topic = BuiltinTopicDcpsSubscription
        else:
            type = "PUBLICATION"
            topic = BuiltinTopicDcpsPublication
        dr = BuiltinDataReader(dp, topic)
        manage_dcps_object(dp, dr, type, args.filename, args.json)

    if args.a is True:
        type = ["PARTICIPANT", "SUBSCRIPTION", "PUBLICATION"]
        dr = [BuiltinDataReader(dp, BuiltinTopicDcpsParticipant),
              BuiltinDataReader(dp, BuiltinTopicDcpsSubscription),
              BuiltinDataReader(dp, BuiltinTopicDcpsPublication)]
        while True:
            for i in range(len(type)):
                manage_dcps_object(dp, dr[i], type[i], args.filename, args.json)


if __name__ == '__main__':
    sys.exit(main())
