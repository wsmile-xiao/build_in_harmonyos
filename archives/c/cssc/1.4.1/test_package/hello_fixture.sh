#!/bin/sh
# cssc test_package fixture: sample source used by the SCCS round-trip
# test.  The conanfile test() imports this file into an SCCS history
# file with "sccs admin -ihello.txt" and retrieves it back with
# "sccs get -s s.hello.txt", then asserts the content round-trips.
hello cssc
This file is the sample used by the test_package round-trip check.
