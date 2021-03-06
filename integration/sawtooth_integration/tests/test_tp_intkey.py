# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import cbor

from sawtooth_processor_test.transaction_processor_test_case \
    import TransactionProcessorTestCase
from sawtooth_integration.message_factories.intkey_message_factory \
    import IntkeyMessageFactory
from sawtooth_sdk.protobuf.validator_pb2 import Message


class TestIntkey(TransactionProcessorTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tester.register_comparator(
            Message.TP_STATE_SET_REQUEST,
            compare_set_request)
        cls.imf = IntkeyMessageFactory()

    def test_set_a(self):
        """
        Test if the intkey processor can set a value.
        """
        tst = self.tester
        imf = self.imf

        # 1. -> Send a set transaction
        #    <- Expect a state get request
        tst.send(imf.create_tp_process_request("set", "a", 5))
        received = tst.expect(imf.create_get_request("a"))

        # 2. -> Send state get response of `None`
        #    <- Expect a state set request
        tst.respond(imf.create_get_response("a", None), received)
        received = tst.expect(imf.create_set_request("a", 5))

        # 3. -> Send a state set response with the address
        #    <- Expect processor response that the transaction was succesful
        tst.respond(imf.create_set_response("a"), received)
        tst.expect(imf.create_tp_response("OK"))

    def test_inc_a(self):
        """
        Test if the processor can increase a value.
        """
        tst = self.tester
        imf = self.imf

        # 1. -> Send an inc transaction
        #    <- Expect a state get request
        tst.send(imf.create_tp_process_request("inc", "c", 2))
        received = tst.expect(imf.create_get_request("c"))

        # 2. -> Send state get response with the value
        #    <- Expect a state set request
        tst.respond(imf.create_get_response("c", 12), received)
        received = tst.expect(imf.create_set_request("c", 14))

        # 3. -> Send a state set response with the address
        #    <- Expect processor response that the transaction was succesful
        tst.respond(imf.create_set_response("c"), received)
        tst.expect(imf.create_tp_response("OK"))

    def test_dec_a(self):
        """
        Test if the processor can decrease a value.
        """
        tst = self.tester
        imf = self.imf

        tst.send(imf.create_tp_process_request("dec", "sawtooth", 1900000000))
        received = tst.expect(imf.create_get_request("sawtooth"))

        tst.respond(imf.create_get_response("sawtooth", 2000000000), received)
        received = tst.expect(imf.create_set_request("sawtooth", 100000000))

        tst.respond(imf.create_set_response("sawtooth"), received)
        tst.expect(imf.create_tp_response("OK"))


def compare_set_request(req1, req2):
    if len(req1.entries) != len(req2.entries):
        return False

    entries1 = [(e.address, cbor.loads(e.data)) for e in req1.entries]
    entries2 = [(e.address, cbor.loads(e.data)) for e in req2.entries]

    return entries1 == entries2
