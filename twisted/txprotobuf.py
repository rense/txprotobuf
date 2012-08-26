# Copyright (c) 2008 Johan Euphrosine
# See LICENSE for details.

from google.protobuf.service import RpcController

class Controller(RpcController):
    def SetFailed(self, reason):
        print "SetFailed:", reason
    def IsCanceled(self):
        pass
    def NotifyOnCancel(self, callback):
        pass

from google.protobuf.service import RpcChannel
from twisted.protocols.basic import Int32StringReceiver
from twisted.internet.defer import Deferred
from txprotobuf_pb2 import Call, Result, Box

class Protocol(RpcChannel, Int32StringReceiver):
    token = 0
    def __init__(self):
        RpcChannel.__init__(self)
        self.pending = {}

    def CallMethod(self, method_descriptor, rpc_controller, request, response_class, done):
        call = Call()
        call.method = method_descriptor.name
        call.request = request.SerializeToString()
        self.token += 1
        call.token = self.token
        d = Deferred()
        d.addCallback(self.parseResponse, response_class)
        d.addCallback(done)
        self.pending[self.token] = d
        box = Box()
        box.call = call.SerializeToString()
        self.sendString(box.SerializeToString())

    def stringReceived(self, data):
        box = Box()
        box.ParseFromString(data)
        if box.call != "":
            call = Call()
            call.ParseFromString(box.call)
            method = self.service.GetDescriptor().FindMethodByName(call.method)
            if method:
                request = self.service.GetRequestClass(method)()
                request.ParseFromString(call.request)
                controller = Controller()
                d = Deferred()
                d.addCallback(self.buildResult, call)
                d.addCallback(self.boxResult)
                d.addCallback(lambda box: self.sendString(box.SerializeToString()))
                self.service.CallMethod(method, controller, request, d.callback)
        elif box.result != "":
            result = Result()
            result.ParseFromString(box.result)
            token = result.token
            if self.pending.has_key(token):
                self.pending[token].callback(result)            

    def parseResponse(self, result, responseClass):
        response = responseClass()
        response.ParseFromString(result.response)
        return response

    def buildResult(self, response, call):
        result = Result()
        result.token = call.token
        result.response = response.SerializeToString()
        return result
    
    def boxResult(self, result):
        box = Box()
        box.result = result.SerializeToString()
        return box

from twisted.internet.protocol import Factory

class Factory(Factory):
    protocol = Protocol
    def __init__(self, service):
        self.protocols = []
        self.service = service
    def buildProtocol(self, address):
        p = self.protocol()
        p.factory = self
        p.service = self.service
        self.protocols.append(p)
        return p

class Proxy:
    def __init__(self, stub):
        self.stub = stub
    def __getattr__(self, name):
        def call(method, request):
            d = Deferred()
            controller = Controller()
            method(controller, request, d.callback)
            return d        
        return lambda request: call(getattr(self.stub, name), request)
