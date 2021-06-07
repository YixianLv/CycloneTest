from cyclonedds.core import Qos, Policy
from dataclasses import fields


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
                    out.append(f"{f.name}<{name_map[f.type]}>")
                else:
                    out.append(f"{f.name}<{f.type}>")
            qos_help.append("-q " f"{policy_name}({','.join(out)})")
    return qos_help
