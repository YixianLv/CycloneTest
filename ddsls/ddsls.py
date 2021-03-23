import sys
import getopt
import json
import uuid

from cyclonedds.domain import DomainParticipant
from cyclonedds.util import isgoodentity
from cyclonedds.builtin import DcpsParticipant,BuiltinDataReader, BuiltinTopicDcpsParticipant, BuiltinTopicDcpsSubscription,  BuiltinTopicDcpsPublication
from cyclonedds.core import Qos


DCPSTOPIC_FLAG = 1
DCPSPARTICIPANT_FLAG = 1 << 1
DCPSSUBSCRIPTION_FLAG = 1 << 2
DCPSPUBLICATION_FLAG = 1 << 3


FLAG = [(DCPSPARTICIPANT_FLAG, "dcpsparticipant"), (DCPSSUBSCRIPTION_FLAG, "dcpssubscription"), (DCPSPUBLICATION_FLAG, "dcpspublication")]


def usage():
    print("Usage: ddsls [FORMAT] [OPTIONS] TOPIC       for specified topics\n")
    print("   or: ddsls [FORMAT] [OPTIONS] -a          for all topics\n")
    print("\nFORMAT:")
    print("--json            --write to file in json format\n")
    print("OPTIONS:")
    print("-f <filename> <topics>            -- write to file\n")
    print("TOPIC:")
    for i in range(len(FLAG)):
        print(FLAG[i][1])


class DcpsObjEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is Qos:
            return obj.asdict()
        if type(obj) is uuid.UUID:
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def print_dcps_object(fp, dp, type, topic, print_json):
    dr = BuiltinDataReader(dp, topic)
    samples = dr.take(N=5)

    for sample in samples:
        if type == 'PARTICIPANT':
            data = {
                "type": type,
                "key": sample.key
            }
        else:
            data = {
                "type": type,
                "key": sample.key,
                "participant_key": sample.participant_key,
                "topic_name": sample.topic_name,
                "qos": sample.qos.asdict()
            }
        if print_json:
            encoded = json.dumps(data, cls=DcpsObjEncoder)
            print(encoded, file=fp)
        else:
            print(data, file=fp)


def manage_dcps_object(flag, fp, dp, print_json):
    if flag & FLAG[0][0]:
        print_dcps_object(fp, dp, 'PARTICIPANT', BuiltinTopicDcpsParticipant, print_json)
    if flag & FLAG[1][0]:
        print_dcps_object(fp, dp, 'SUBSCRIPTION', BuiltinTopicDcpsSubscription, print_json)
    if flag & FLAG[2][0]:
        print_dcps_object(fp, dp, 'PUBLICATION', BuiltinTopicDcpsPublication, print_json)


def main():
    fp = sys.stdout
    print_json = False
    flag = 0
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:a", ["json"])
        if len(sys.argv) == 1:
            usage()
            sys.exit()
    except getopt.GetoptError:
        usage()
        sys.exit()
    for opt, arg in opts:
        if opt == '-f':
            fp = open(arg, mode='w')
            print(" Result has been written to file '" + arg + "'")
            if fp is None:
                print(arg + ": can't open for writing")
                exit(1)
        elif opt == '--json':
            print_json = True
        elif opt == '-a':
            pass
        else:
            usage()
            sys.exit()
    for arg in args:
        for i in range(len(FLAG)):
            if arg == FLAG[i][1]:
                flag |= FLAG[i][0]
                break
            elif i == len(FLAG)-1:
                print(arg + " topic unknow")
                sys.exit()

    dp = DomainParticipant(0)
    if flag == 0:
        for i in range(len(FLAG)):
            flag |= FLAG[i][0]
    manage_dcps_object(flag, fp, dp, print_json)

    fp.close()


if __name__ == '__main__':
    main()
