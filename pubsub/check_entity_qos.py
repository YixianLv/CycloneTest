from cyclonedds.core import Qos
from entity_qos import EntityQosMapper


eqos = [None] * 5


def entity_qos(qos, entity):
    if entity == "topic":
        eqos[0] = check_entity_qos("topic", EntityQosMapper.topic, qos)
    elif entity == "publisher":
        eqos[1] = check_entity_qos("publisher", EntityQosMapper.pubsub, qos)
    elif entity == "subscriber":
        eqos[2] = check_entity_qos("subscriber", EntityQosMapper.pubsub, qos)
    elif entity == "datawriter":
        eqos[3] = check_entity_qos("datawriter", EntityQosMapper.writer, qos)
    elif entity == "datareader":
        eqos[4] = check_entity_qos("datareader", EntityQosMapper.reader, qos)
    else:  # qos-all
        for e in ["topic", "publisher", "subscriber", "datawriter", "datareader"]:
            entity_qos(qos, e)
    return eqos


def check_entity_qos(e, eqos_mapper, qos):
    eq = []
    for q in qos:
        policy_scope = f"Policy.{q.__scope__}"

        if policy_scope in eqos_mapper:
            eq.append(q)
        else:
            print(f"The {q} is not applicable for {e}, will be ignored.")
    return Qos(*eq)
