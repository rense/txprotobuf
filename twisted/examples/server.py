# Copyright (c) 2008 Johan Euphrosine
# See LICENSE for details.

import txprotobuf

from test.test_pb2 import TestService, TestResponse

class ServerTestService(TestService):
    def TestMethod(self, controller, testRequest, callback):
        response = TestResponse()
        response.text = testRequest.text
        print "TestMethod", testRequest.text
        callback(response)
        
from twisted.application import service, internet

testService = ServerTestService()
factory = txprotobuf.Factory(testService)
application = service.Application("TestService")
internet.TCPServer(1234, factory).setServiceParent(application)
