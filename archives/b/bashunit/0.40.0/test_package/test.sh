#!/usr/bin/env bash

function test_packaged_bashunit_executes_a_real_test() {
  assert_same "bashunit works" "$(printf '%s' 'bashunit works')"
}
