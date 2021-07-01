from cyclonedds.core import Qos
from entity_qos import EntityQosMapper


eqos = [None] * 5


def entity_qos(qos, entity):
    if entity == "qos-topic":
        eqos[0] = check_entity_qos("topic", EntityQosMapper.topic, qos)
    elif entity == "qos-publisher":
        eqos[1] = check_entity_qos("publisher", EntityQosMapper.pubsub, qos)
    elif entity == "qos-subscriber":
        eqos[2] = check_entity_qos("subscriber", EntityQosMapper.pubsub, qos)
    elif entity == "qos-datawriter":
        eqos[3] = check_entity_qos("datawriter", EntityQosMapper.writer, qos)
    elif entity == "qos-datareader":
        eqos[4] = check_entity_qos("datareader", EntityQosMapper.reader, qos)
    else:  # qos-all
        for e in ["qos-topic", "qos-publisher", "qos-subscriber", "qos-datawriter", "qos-datareader"]:
            entity_qos(qos, e)
    return eqos


def check_entity_qos(e, eqos_mapper, qos):
    eqos = []
    for q in qos:
        policy_scope = f"Policy.{q.__scope__}"

        if policy_scope in eqos_mapper:
            eqos.append(q)
        else:
            print(f"The {q} is not applicable for {e}, will be ignored.")
    return Qos(*eqos)
