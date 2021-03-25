#!/usr/bin/env python3

import sys
import json
import argparse

from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import (BuiltinDataReader, BuiltinTopicDcpsParticipant,
                                BuiltinTopicDcpsSubscription,  BuiltinTopicDcpsPublication)
from cyclonedds.core import Listener


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, help="define the domain participant id", default=0)
    parser.add_argument("--filename", nargs="?", type=argparse.FileType("w"), help="write to file", default=sys.stdout)
    parser.add_argument("--json", action="store_true", help="print output in JSON format")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", action="store_true", help="for all topics")
    group.add_argument("--topics", choices=["dcpsparticipant", "dcpssubscription", "dcpspublication"])
    args = parser.parse_args()
    return args


class MyListener(Listener):
    def on_data_available(self, dr):
        pass


def print_dcps_object(fp, dp, topic_type, topic, print_json):
    listener = MyListener()
    dr = BuiltinDataReader(dp, topic, listener=listener)

    samples = dr.take(N=100)
    if samples:
        for sample in samples:
            if topic_type == 'PARTICIPANT':
                sample = {
                    topic_type: [{
                        "key": str(sample.key)
                    }]
                }
            else:
                sample = {
                    topic_type: [{
                        "key": str(sample.key),
                        "participant_key": str(sample.participant_key),
                        "topic_name": sample.topic_name,
                        "qos": sample.qos.asdict()
                    }]
                }
            if print_json:
                json.dump(sample, fp, indent=4)
            else:
                fp.write(str(sample))


def main():
    args = create_parser()
    dp = DomainParticipant(args.id)
    if args.topics == "dcpsparticipant":
        type = "PARTICIPANT"
        topic = BuiltinTopicDcpsParticipant
    elif args.topics == "dcpssubscription":
        type = "SUBSCRIPTION"
        topic = BuiltinTopicDcpsSubscription
    else:
        type = "PUBLICATION"
        topic = BuiltinTopicDcpsPublication
    print_dcps_object(args.filename, dp, type, topic, args.json)

    if args.a is True:
        type = ["PARTICIPANT", "SUBSCRIPTION", "PUBLICATION"]
        topic = [BuiltinTopicDcpsParticipant, BuiltinTopicDcpsSubscription, BuiltinTopicDcpsPublication]
        for i in range(len(type)):
            print_dcps_object(args.filename, dp, type[i], topic[i], args.json)

    args.filename.close()


if __name__ == '__main__':
    sys.exit(main())
