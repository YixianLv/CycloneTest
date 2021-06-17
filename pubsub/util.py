from cyclonedds.core import Qos, Policy
from dataclasses import fields
import typing


dds_infinity = 9223372036854775807


default_qos_val = {
    "Policy.Deadline": [dds_infinity],
    "Policy.DurabilityService": [0, Policy.History.KeepLast(1), dds_infinity, dds_infinity, dds_infinity],
    "Policy.Groupdata": ["".encode()],
    "Policy.History.KeepLast": [1],
    "Policy.LatencyBudget": [0],
    "Policy.Lifespan": [dds_infinity],
    "Policy.Liveliness.Automatic": [dds_infinity],
    "Policy.Liveliness.ManualByParticipant": [dds_infinity],
    "Policy.Liveliness.ManualByTopic": [dds_infinity],
    "Policy.OwnershipStrength": [0],
    "Policy.Partition": [""],
    "Policy.PresentationAccessScope.Instance": [False, False],
    "Policy.PresentationAccessScope.Topic": [False, False],
    "Policy.PresentationAccessScope.Group": [False, False],
    "Policy.ReaderDataLifecycle": [dds_infinity, dds_infinity],
    "Policy.Reliability.BestEffort": [100],
    "Policy.Reliability.Reliable": [100],
    "Policy.ResourceLimits": [dds_infinity, dds_infinity, dds_infinity],
    "Policy.TimeBasedFilter": [0],
    "Policy.Topicdata": ["".encode()],
    "Policy.TransportPriority": [0],
    "Policy.Userdata": ["".encode()],
    "Policy.WriterDataLifecycle": [True]
}


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
            qos_help.append("-q " f"{policy_name}")
        else:
            out = []
            d_val = []
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
            for d in default_qos_val[name]:
                if d == dds_infinity:
                    d_val.append("inf")
                elif d == "":
                    d_val.append("''")
                else:
                    d_val.append(str(d))
            qos_help.append("-q " f"{policy_name} {', '.join(out)}\n   (default: {', '.join(d_val)})")
    return qos_help


qos_help_msg = str('''e.g.:
    -q Durability.TransientLocal
    -q History.KeepLast 10
    -q ReaderDataLifecycle 10, 20
    -q Partition [a, b, 123]
    -q PresentationAccessScope.Instance False, True
    -q DurabilityService 1000, History.KeepLast 10, 100, 10, 10\n\n''' +
                   "Available QoS and usage are:\n" + "\n".join(map(str, qos_help())))


class QosMapper():
    topic = {
        "Policy.Deadline",
        "Policy.DestinationOrder.ByReceptionTimestamp",
        "Policy.DestinationOrder.BySourceTimestamp",
        "Policy.Durability.Volatile",
        "Policy.Durability.TransientLocal",
        "Policy.Durability.Transient",
        "Policy.Durability.Persistent",
        "Policy.DurabilityService",
        "Policy.History.KeepLast",
        "Policy.History.KeepAll",
        "Policy.LatencyBudget",
        "Policy.Lifespan",
        "Policy.Liveliness.Automatic",
        "Policy.Liveliness.ManualByParticipant",
        "Policy.Liveliness.ManualByTopic",
        "Policy.Ownership.Shared",
        "Policy.Ownership.Exclusive",
        "Policy.Reliability.BestEffort",
        "Policy.Reliability.Reliable",
        "Policy.ResourceLimits",
        "Policy.Topicdata",
        "Policy.TransportPriority"
    }

    pubsub = {
        "Policy.Groupdata",
        "Policy.Partition",
        "Policy.PresentationAccessScope.Instance",
        "Policy.PresentationAccessScope.Topic",
        "Policy.PresentationAccessScope.Group"
    }

    writer = {
        "Policy.Deadline",
        "Policy.DestinationOrder.ByReceptionTimestamp",
        "Policy.DestinationOrder.BySourceTimestamp",
        "Policy.Durability.Volatile",
        "Policy.Durability.TransientLocal",
        "Policy.Durability.Transient",
        "Policy.Durability.Persistent",
        "Policy.DurabilityService",
        "Policy.History.KeepLast",
        "Policy.History.KeepAll",
        "Policy.LatencyBudget",
        "Policy.Lifespan",
        "Policy.Liveliness.Automatic",
        "Policy.Liveliness.ManualByParticipant",
        "Policy.Liveliness.ManualByTopic",
        "Policy.Ownership.Shared",
        "Policy.Ownership.Exclusive",
        "Policy.OwnershipStrength",
        "Policy.Reliability.BestEffort",
        "Policy.Reliability.Reliable",
        "Policy.ResourceLimits",
        "Policy.TransportPriority",
        "Policy.Userdata",
        "WriterDataLifecycle"
    }

    reader = {
        "Policy.Deadline",
        "Policy.DestinationOrder.ByReceptionTimestamp",
        "Policy.DestinationOrder.BySourceTimestamp",
        "Policy.Durability.Volatile",
        "Policy.Durability.TransientLocal",
        "Policy.Durability.Transient",
        "Policy.Durability.Persistent",
        "Policy.History.KeepLast",
        "Policy.History.KeepAll",
        "Policy.LatencyBudget",
        "Policy.Liveliness.Automatic",
        "Policy.Liveliness.ManualByParticipant",
        "Policy.Liveliness.ManualByTopic",
        "Policy.Ownership.Shared",
        "Policy.Ownership.Exclusive",
        "Policy.ReaderDataLifecycle",
        "Policy.Reliability.BestEffort",
        "Policy.Reliability.Reliable",
        "Policy.ResourceLimits",
        "Policy.TimeBasedFilter",
        "Policy.Userdata"
    }
