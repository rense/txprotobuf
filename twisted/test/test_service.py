# Copyright (c) 2008 Johan Euphrosine
# See LICENSE for details.

from twisted.trial import unittest
from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.internet.protocol import ClientCreator

import txprotobuf

from test.test_pb2 import TestService, TestService_Stub, TestRequest, TestResponse

class ServerTestService(TestService):
    d = None
    def waitFromTestMethodCall(self):
        self.d = Deferred()
        return self.d
    def TestMethod(self, controller, testRequest, callback):
        if self.d: self.d.callback(testRequest.text)
        response = TestResponse()
        response.text = testRequest.text
        callback(response)

class ClientTestService(TestService):
    def TestMethod(self, controller, testRequest, callback):
        response = TestResponse()
        response.text = testRequest.text
        callback(response)

class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.service = ServerTestService()
        self.service.factory = txprotobuf.Factory(self.service)
        self.port = reactor.listenTCP(0, self.service.factory)
        self.protocols = []
    def tearDown(self):
        for protocol in self.protocols:
            protocol.transport.loseConnection()
        for protocol in self.service.factory.protocols:
            protocol.transport.loseConnection()
        return self.port.stopListening()
    def connectClient(self):
        d = ClientCreator(reactor, txprotobuf.Protocol).connectTCP(self.port.getHost().host, self.port.getHost().port)
        def setProtocol(protocol):
            self.protocols.append(protocol)
            return protocol
        d.addCallback(setProtocol)
        return d
    def testMethodCall(self):
        d = self.connectClient()
        def callTestMethod(protocol):
            channel = protocol
            controller = txprotobuf.Controller()
            service = TestService_Stub(channel)
            request = TestRequest()
            request.text = "foo"
            d = self.service.waitFromTestMethodCall()
            def checkTestMethodCalled(text):
                self.assertEquals(request.text, text)
            d.addCallback(checkTestMethodCalled)
            waitForMethodResponse = Deferred()
            d.addCallback(lambda x: waitForMethodResponse)
            waitForMethodResponse.addCallback(lambda response: self.assertEquals(request.text, response.text))
            def callback(response):
                waitForMethodResponse.callback(response)
            service.TestMethod(controller, request, callback)
            return d
        d.addCallback(callTestMethod)
        return d
    def testConcurrentMethodCall(self):
        d = self.connectClient()
        def callTestMethod(protocol):
            channel = protocol
            controller = txprotobuf.Controller()
            service = TestService_Stub(channel)
            requestFoo = TestRequest()
            requestFoo.text = "foo"
            waitFoo = Deferred()
            waitFoo.addCallback(lambda responseFoo: self.assertEquals(responseFoo.text, requestFoo.text))
            service.TestMethod(controller, requestFoo, waitFoo.callback)
            requestBar = TestRequest()
            requestBar.text = "bar"
            waitBar = Deferred()
            waitBar.addCallback(lambda responseBar: self.assertEquals(responseBar.text, requestBar.text))
            service.TestMethod(controller, requestBar, waitBar.callback)
            return DeferredList([waitFoo, waitBar])
            
        d.addCallback(callTestMethod)
        return d
    def testBidirectionalCall(self):
        d = self.connectClient()
        def clientConnected(protocol):
            protocol.service = ClientTestService()
            channel = self.service.factory.protocols[0]
            controller = txprotobuf.Controller()
            service = TestService_Stub(channel)
            request = TestRequest()
            request.text = "reverse"
            wait = Deferred()
            wait.addCallback(lambda response: self.assertEquals(response.text, request.text))
            service.TestMethod(controller, request, wait.callback)
            return wait
        d.addCallback(clientConnected)
        return d
    def testProxy(self):
        d = self.connectClient()
        def clientConnected(protocol):
            proxy = txprotobuf.Proxy(TestService_Stub(protocol))
            request = TestRequest()
            request.text = "proxycall"
            d = proxy.TestMethod(request)
            d.addCallback(lambda response: self.assertEquals(response.text, request.text))
            return d
        d.addCallback(clientConnected)
        return d
