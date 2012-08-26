# Copyright (c) 2008 Johan Euphrosine
# See LICENSE for details.

all: proto

proto:
	protoc -Iprotobuf --python_out=twisted protobuf/txprotobuf.proto
	protoc -Iprotobuf --python_out=twisted/test protobuf/test.proto

check: proto
	cd twisted && trial test/test_service.py

clean:
	find . | grep '\.pyc$$' | xargs rm -f
	find . | grep '~$$' | xargs rm -f
	find . | grep '_pb2.py$$' | xargs rm -f
	rm -fR twisted/_trial_temp

.PHONY: all
