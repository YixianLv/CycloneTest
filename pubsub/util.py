from cyclonedds.core import Qos
from dataclasses import fields
import typing


def qos_help():
    name_map = {
        int: 'integer',
        str: 'string',
        float: 'float',
        bool: 'boolean',
        bytes: 'bytes'
    }
    qos_help = []
    for policy_name, policy in Qos._policy_mapper.items():
        policy_name = policy_name.strip("Policy.")
        _fields = fields(policy)
        if len(_fields) == 0:
            qos_help.append("-q " f"{policy_name}")
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
            qos_help.append("-q " f"{policy_name} {', '.join(out)}")
    return qos_help


qos_help_msg = str('''e.g.:
    -q Durability.TransientLocal
    -q History.KeepLast 10
    -q ReaderDataLifecycle 10, 20
    -q Partition [a, b, 123]
    -q PresentationAccessScope.Instance False, True
    -q DurabilityService 1000, History.KeepLast 10, 100, 10, 10\n\n''' +
                   "Available QoS and usage are:\n" + "\n".join(map(str, qos_help())))
