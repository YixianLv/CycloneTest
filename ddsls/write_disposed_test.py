#!/usr/bin/env python3
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
import json
from pycdr import cdr


@cdr
class Message:
    msg: str


dp = DomainParticipant(0)
tp = Topic(dp, "MessageTopic", Message)
dw = DataWriter(dp, tp)
dr = DataReader(dp, tp)

data = {
    "dp.guid": str(dp.guid),
    "tp.name": tp.name,
    "tp.typename": tp.typename,
    "dw.guid": str(dw.guid),
    "dr.guid": str(dr.guid)
}

print(json.dumps(data, indent=4))
