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
                        out.append("[Policy.History.KeepAll / Policy.History.KeepLast [depth<integer>]]")
                    elif f.type is typing.Sequence[str]:
                        out.append(f"[{f.name}<Sequence[str]>]")
                    else:
                        out.append(f"[{f.name}<{f.type}>]")
            qos_help.append("-q " f"{policy_name} {', '.join(out)}")
    return qos_help


qos_help_msg = str('''e.g.:
    -q Policy.Durability.TransientLocal
    -q Policy.History.KeepLast 10
    -q Policy.ReaderDataLifecycle 10, 20
    -q Policy.DurabilityService 10, Policy.History.KeepLast 20, 30, 40, 50\n\n''' +
                   "Available QoS and usage are:\n" + "\n".join(map(str, qos_help())))
