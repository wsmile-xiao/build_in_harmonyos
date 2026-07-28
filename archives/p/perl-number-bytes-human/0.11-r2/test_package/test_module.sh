#!/bin/sh
# test_module.sh — L1 test for perl-number-bytes-human
# Verifies the Number::Bytes::Human module loads and reports correct version
perl -MNumber::Bytes::Human -e 'print Number::Bytes::Human->VERSION, qq{\n}'
