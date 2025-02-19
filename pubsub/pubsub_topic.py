from datastruct import Integer, String, IntArray, StrArray, IntSequence, StrSequence
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.topic import Topic
from cyclonedds.core import Listener, DDSException, ReadCondition, ViewState, InstanceState, SampleState


class QosListener(Listener):
    def on_requested_incompatible_qos(self, reader, status):
        print("WARNING: The Qos requested for subscription is incompatible with the Qos offered by publication." +
              "PubSub may not be available.")


class TopicManager():
    def __init__(self, args, dp, qos, waitset):
        self.dp = dp
        self.topic_name = args.topic
        self.seq = -1
        self.tqos, self.pqos, self.sqos, self.wqos, self.rqos = qos
        self.reader = []
        try:
            self.listener = QosListener()
            self.pub = Publisher(dp, qos=self.pqos)
            self.sub = Subscriber(dp, qos=self.sqos)
            self.int_writer = self.create_entities("int", Integer)
            self.str_writer = self.create_entities("str", String)
            self.int_array_writer = self.create_entities("int_array", IntArray)
            self.str_array_writer = self.create_entities("str_array", StrArray)
            self.int_seq_writer = self.create_entities("int_seq", IntSequence)
            self.str_seq_writer = self.create_entities("str_seq", StrSequence)
        except DDSException:
            raise Exception("The arguments inputted are considered invalid for cyclonedds.")

        self.read_cond = ReadCondition(self.reader[0], ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(self.read_cond)

    def write(self, input):
        self.seq += 1
        # Write integer
        if type(input) is int:
            self.int_writer.write(Integer(self.seq, input))
        elif type(input) is list:
            for i in input:
                if not isinstance(i, type(input[0])):  # Check if elements in the list are the same type
                    raise Exception("TypeError: Element type inconsistent, " +
                                    "input list should be a list of integer or a list of string.")

            # Write array or sequence of integer
            if isinstance(input[0], int):
                int_arr_len = IntArray.__annotations__['keyval'].__metadata__[0].length
                if len(input) == int_arr_len:
                    self.int_array_writer.write(IntArray(self.seq, input))
                else:
                    self.int_seq_writer.write(IntSequence(self.seq, input))
            # Write array or sequence of string
            else:
                str_arr_len = StrArray.__annotations__['keyval'].__metadata__[0].length
                if len(input) == str_arr_len:
                    self.str_array_writer.write(StrArray(self.seq, input))
                else:
                    self.str_seq_writer.write(StrSequence(self.seq, input))
        # Write string
        else:
            self.str_writer.write(String(self.seq, input))

    def read(self):
        for reader in self.reader:
            for sample in reader.take(N=100):
                print(f"Subscriberd: {sample}")

    def create_entities(self, name, datastruct):
        topic = Topic(self.dp, self.topic_name + name, datastruct, qos=self.tqos)
        writer = DataWriter(self.pub, topic, qos=self.wqos)
        # Create a list of readers
        if name == "int":
            self.reader.append(DataReader(self.sub, topic, qos=self.rqos, listener=self.listener))
        else:
            self.reader.append(DataReader(self.sub, topic, qos=self.rqos))
        return writer
