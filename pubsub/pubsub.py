#!/usr/bin/env python3
import sys
import select

from util import create_parser
from check_entity_qos import entity_qos
from parse_qos import QosParser
from pubsub_topic import TopicManager
from cyclonedds.core import WaitSet
from cyclonedds.domain import DomainParticipant
from cyclonedds.util import duration


def main():
    eqos = [None] * 5
    args = create_parser()
    if args.qos:
        qos = QosParser.parse(args.qos)
        eqos = entity_qos(qos, args.entity)

    dp = DomainParticipant(0)
    waitset = WaitSet(dp)
    manager = TopicManager(args, dp, eqos, waitset)
    if args.topic:
        try:
            while True:
                input = select.select([sys.stdin], [], [], 0)[0]
                if input:
                    for text in sys.stdin.readline().split():
                        try:  # integer or list
                            text = eval(text)
                            manager.write(text)
                        except NameError:  # string
                            manager.write(text.rstrip("\n"))
                manager.read()
                waitset.wait(duration(microseconds=20))
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
