import pytest
import os
import sys
import io
import asyncio
import concurrent

import subprocess

from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.core import Qos, Policy, WaitSet, ReadCondition, ViewState, InstanceState, SampleState


# Helper functions


text = "test 420 [4,2,0] ['test','str','array','data','struct'] [2,183] ['test','string','sequence']"


def run_pubsub(args, timeout=10):
    process = subprocess.Popen(["python3",
                               os.path.join(os.path.dirname(__file__), "..", "tools", "pubsub", "pubsub.py")] + args,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               )
    try:
        process.stdin.write(text.encode())
        stdout, stderr = process.communicate(timeout=timeout)
        process.stdin.close()
    except subprocess.TimeoutExpired as e:
        process.kill()
        raise e

    return {
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
        "status": process.returncode
    }


def run_ddsls(arguments):
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "tools"))
    old_stderr, old_stdout = sys.stderr, sys.stdout
    sys.stderr = io.StringIO()
    sys.stdout = io.StringIO()
    from ddsls import main
    returnv = main(arguments)
    stderr = sys.stderr.getvalue()
    stdout = sys.stdout.getvalue()
    sys.stderr = old_stderr
    sys.stdout = old_stdout
    return {
        "stdout": stdout.replace("\r", ""),
        "stderr": stderr.replace("\r", ""),
        "status": returnv
    }


async def run_pubsub_ddsls_async(pubsub_args, ddsls_args, runtime):
    loop = asyncio.get_event_loop_policy().get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        pubsub_task = loop.run_in_executor(pool, run_pubsub, ["--runtime", str(runtime-2)] + pubsub_args)
        ddsls_task = loop.run_in_executor(pool, run_ddsls, ["--watch", "--runtime", str(runtime)] + ddsls_args)
        await asyncio.sleep(0.3)
        return (await pubsub_task), (await ddsls_task)


def run_pubsub_ddsls(pubsub_args, ddsls_args, runtime=5):
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(run_pubsub_ddsls_async(pubsub_args, ddsls_args, runtime))
    return result


# tests


def test_pubsub_topics():
    pubsub = run_pubsub(["-T", "test", "--runtime", "1"])

    assert "String(seq=0, keyval='test')" in pubsub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert "IntArray(seq=2, keyval=[4, 2, 0])" in pubsub["stdout"]
    assert "StrArray(seq=3, keyval=['test', 'str', 'array', 'data', 'struct'])" in pubsub["stdout"]
    assert "IntSequence(seq=4, keyval=[2, 183])" in pubsub["stdout"]
    assert "StrSequence(seq=5, keyval=['test', 'string', 'sequence'])" in pubsub["stdout"]


def test_qos():
    pubsub, ddsls = run_pubsub_ddsls(["-T", "test", "--qos", "Durability.TransientLocal"],
                                     ["-a"],
                                     runtime=3)

    assert "Durability.TransientLocal" in ddsls["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_multiple_qoses():
    pubsub, ddsls = run_pubsub_ddsls(["-T", "test", "--qos", "Durability.TransientLocal", "Userdata HelloWorld"],
                                     ["-a"],
                                     runtime=3)

    assert "Userdata(data=b'HelloWorld')" in ddsls["stdout"]
    assert "Durability.TransientLocal" in ddsls["stdout"]

    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_qos_special_cases():
    pubsub, ddsls = run_pubsub_ddsls(["-T", "test", "--qos", "PresentationAccessScope.Topic:", "True, False",
                                      "Partition", "test, parti, 33",
                                      "DurabilityService", "seconds=1, history.keeplast 10, 100, 10, 10",
                                      "Topicdata", "helloTopic"],
                                     ["-a"],
                                     runtime=3)

    assert "PresentationAccessScope.Topic(coherent_access=True, ordered_access=False)" in ddsls["stdout"]
    assert "Partition(partitions=('test', 'parti', '33'))" in ddsls["stdout"]
    assert "DurabilityService(cleanup_delay=1000000000, history=Policy.History.KeepLast(depth=10), \
max_samples=100, max_instances=10, max_samples_per_instance=10)" in ddsls["stdout"]
    assert "Topicdata(data=b'helloTopic')" in ddsls["stdout"]

    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_topic_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_topic_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal", "ResourceLimits", "100, 10, 10"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "ResourceLimits(max_samples=100, max_instances=10, max_samples_per_instance=10)" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal", "ResourceLimits", "100, 10, 10"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]
    assert "ResourceLimits(max_samples=100, max_instances=10, max_samples_per_instance=10)" in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_publisher_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_publisher_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True", "Groupdata", "TestPublisherQos"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_pub["stdout"]
    assert "Groupdata(data=b'TestPublisherQos')" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True", "Groupdata", "TestPublisherQos"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_sub["stdout"]
    assert "Groupdata(data=b'TestPublisherQos')" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_subscriber_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_subscriber_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True", "Groupdata", "TestSubscriberQos"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_pub["stdout"]
    assert "Groupdata(data=b'TestSubscriberQos')" not in ddsls_pub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True", "Groupdata", "TestSubscriberQos"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_sub["stdout"]
    assert "Groupdata(data=b'TestSubscriberQos')" in ddsls_sub["stdout"]


def test_writer_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "Durability.TransientLocal" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_writer_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal", "TransportPriority", "10"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "TransportPriority(priority=10)" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal", "TransportPriority", "10"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "Durability.TransientLocal" not in ddsls_sub["stdout"]
    assert "TransportPriority(priority=10)" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_reader_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "Durability.TransientLocal" not in ddsls_pub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]


def test_reader_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal", "LatencyBudget", "10"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "Durability.TransientLocal" not in ddsls_pub["stdout"]
    assert "LatencyBudget(budget=10)" not in ddsls_pub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal", "LatencyBudget", "10"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]
    assert "LatencyBudget(budget=10)" in ddsls_sub["stdout"]


def test_not_applicable_entity_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test",
                                          "--qos", "WriterDataLifecycle", "False"],
                                         ["-t", "dcpspublication"], runtime=3)

    assert "WriterDataLifecycle(autodispose=False)" in ddsls_pub["stdout"]
    assert "Policy.WriterDataLifecycle(autodispose=False) is not applicable for topic" in pubsub["stdout"]
    assert "Policy.WriterDataLifecycle(autodispose=False) is not applicable for publisher" in pubsub["stdout"]
    assert "Policy.WriterDataLifecycle(autodispose=False) is not applicable for subscriber" in pubsub["stdout"]
    assert "Policy.WriterDataLifecycle(autodispose=False) is not applicable for datareader" in pubsub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test",
                                          "--qos", "WriterDataLifecycle", "False"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "WriterDataLifecycle(autodispose=False)" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_incompatible_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "--qos", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpspublication"], runtime=3)
    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_pub["stdout"]
    assert "The Qos requested for subscription is incompatible with the Qos offered by publication" in pubsub["stdout"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "--qos", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpssubscription"], runtime=3)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_sub["stdout"]
    assert "The Qos requested for subscription is incompatible with the Qos offered by publication" in pubsub["stdout"]

    assert "Integer(seq=1, keyval=420)" not in pubsub["stdout"]
    assert "String" not in pubsub["stdout"]
    assert "IntArray" not in pubsub["stdout"]
    assert "StrArray" not in pubsub["stdout"]
    assert "IntSequence" not in pubsub["stdout"]
    assert "StrSequence" not in pubsub["stdout"]


def test_qos_help():
    pubsub = run_pubsub(["--qoshelp"])
    assert "Available QoS and usage" in pubsub["stdout"]
    assert "--qos Reliability.BestEffort" in pubsub["stdout"]
    assert "--qos Reliability.Reliable [max_blocking_time<integer>]" in pubsub["stdout"]
    assert "--qos Partition [partitions<Sequence[str]>]" in pubsub["stdout"]
    assert "--qos DurabilityService [cleanup_delay<integer>], [History.KeepAll / History.KeepLast [depth<integer>]], \
[max_samples<integer>], [max_instances<integer>], [max_samples_per_instance<integer>]" in pubsub["stdout"]
