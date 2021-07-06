from cyclonedds.core import Qos
from dataclasses import fields
import typing
import sys
import argparse


def qos_help():
    name_map = {
        int: 'integer',
        str: 'string',
        float: 'float',
        bool: 'boolean',
        bytes: 'bytes'
    }
    qos_help = []
    for name, policy in Qos._policy_mapper.items():
        policy_name = name.replace("Policy.", "")
        _fields = fields(policy)
        if len(_fields) == 0:
            qos_help.append("--qos " f"{policy_name}\n")
        else:
            out = []
            for f in _fields:
                if f.type in name_map:
                    out.append(f"[{f.name}<{name_map[f.type]}>]")
                else:
                    if f.type.__origin__ is typing.Union:
                        out.append("[History.KeepAll / History.KeepLast [depth<integer>]]")
                    elif f.type is typing.Sequence[str]:
                        out.append(f"[{f.name}<Sequence[str]>]")
                    else:
                        out.append(f"[{f.name}<{f.type}>]")
            qos_help.append("--qos " f"{policy_name} {', '.join(out)}\n")
    return qos_help


qos_help_msg = str(f"""e.g.:
    --qos Durability.TransientLocal
    --qos History.KeepLast 10
    --qos ReaderDataLifecycle 10, 20
    --qos Partition [a, b, 123]
    --qos PresentationAccessScope.Instance False, True
    --qos DurabilityService 1000, History.KeepLast 10, 100, 10, 10
    --qos Durability.TransientLocal History.KeepLast 10\n
    \rAvailable QoS and usage are:\n {' '.join(map(str, qos_help()))}\n""")


def create_parser(args):
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-T", "--topic", type=str, help="The name of the topic to publish/subscribe to")
    parser.add_argument("-eqos", "--entityqos", choices=["all", "topic", "publisher", "subscriber",
                        "datawriter", "datareader"], help="""Select the entites to set the qos.
Choose between all entities, topic, publisher, subscriber, datawriter and datareader. (default: all).
Inapplicable qos will be ignored.""")
    parser.add_argument("-q", "--qos", nargs="+",
                        help="Set QoS for entities, check '--qoshelp' for available QoS and usage\n")
    group.add_argument("--qoshelp", action="store_true", help=qos_help_msg)
    parser.add_argument("-r", "--runtime", type=float, help="Limit the runtime of the tool, in seconds.")
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
    args = parser.parse_args(args)
    if args.qoshelp:
        print(qos_help_msg)
        sys.exit(0)
    if args.entityqos and not args.qos:
        raise SystemExit("Error: The following argument is required: -q/--qos")
    return args
