proc assert_equal {label actual expected} {
    if {$actual ne $expected} {
        puts stderr "FAIL $label: expected '$expected', got '$actual'"
        exit 1
    }
    puts "PASS $label: $actual"
}

assert_equal "patchlevel" [info patchlevel] "8.6.16"
assert_equal "arithmetic" [expr {21 * 2}] "42"
assert_equal "list length" [llength {alpha beta gamma}] "3"
assert_equal "dictionary size" [dict size [dict create name Tcl version 8.6.16]] "2"

set init_file [file join [info library] init.tcl]
assert_equal "runtime init.tcl" [file exists $init_file] "1"

set msgcat_version [package require msgcat 1.6]
assert_equal "msgcat package" \
    [expr {[package vcompare $msgcat_version 1.6] >= 0}] "1"
assert_equal "clock format" \
    [clock format 0 -gmt true -format "%Y-%m-%d"] "1970-01-01"

puts "PASS tclsh8.6 consumer"
