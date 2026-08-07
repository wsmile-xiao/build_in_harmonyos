# test.als — afnix 3.8.0 consumer test
# Mirrors upstream tst/ref/AXI0001.als assert form (smoke test)

# basic assertions (exit 0 on success, non-zero on failure)
assert nil     nil
assert 2000    2000
assert 0.0     0.0
assert true    true
assert false   false
assert 'a'     'a'
assert "hello" "hello"

# confirm the interpreter can evaluate and print
println "afnix 3.8.0 test_package: OK"
