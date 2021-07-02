import pytest
import json
import time
import os
import sys

import subprocess

from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.core import Qos, Policy, WaitSet, ReadCondition, ViewState, InstanceState, SampleState


# Helper functions


def run_pubsub(args, text, timeout=100):
    os.path.join(os.path.dirname(__file__), "..", "tools", "pubsub", "pubsub.py")
    pubsub_process = subprocess.Popen(["python3", os.path.join(os.path.dirname(__file__), "..", "tools", "pubsub", "pubsub.py")],
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      )

    try:
        pubsub_process.stdin.write(text.encode())
        stdout, stderr = pubsub_process.communicate(timeout=timeout)
        # time.sleep(5)
    except subprocess.TimeoutExpired as e:
        pubsub_process.kill()
        raise e

    return {
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
        "status": pubsub_process.returncode
    }


# test


def test_run():
    data = run_pubsub(["-T", "test", "-r", "1000"], "test string")
    assert data["stdout"] is None
