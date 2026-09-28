set package_dir [lindex $argv 0]
lappend auto_path $package_dir

set ::passed 0
proc check {name condition} {
    if {![uplevel 1 [list expr $condition]]} {
        error "FAIL: $name"
    }
    incr ::passed
    puts "PASS: $name"
}

check package-version {[package require Memchan 2.3] eq "2.3"}

set channel [memchan]
puts -nonewline $channel "HarmonyOS PC"
seek $channel 0
check memchan-roundtrip {[read $channel] eq "HarmonyOS PC"}
close $channel

set channel [fifo]
puts -nonewline $channel "fifo"
check fifo-roundtrip {[read $channel] eq "fifo"}
close $channel

set channel [null]
check null-channel {[read $channel] eq ""}
close $channel

set channel [zero]
set zero_data [read $channel 16]
check zero-channel {
    [string length $zero_data] == 16
    && [binary encode hex $zero_data] eq [string repeat 00 16]
}
close $channel

set channel [random]
check random-channel {[string length [read $channel 32]] == 32}
close $channel

# HarmonyOS-specific: exercise delayed nonblocking channel notification through
# the platform event loop, a path that is sensitive to OHOS timer semantics.
set channel [zero]
fconfigure $channel -blocking 0 -delay 1
set ::ready 0
fileevent $channel readable {set ::ready 1}
set timeout [after 1000 {set ::ready -1}]
vwait ::ready
after cancel $timeout
fileevent $channel readable {}
close $channel
check ohos-delayed-fileevent {$::ready == 1}

puts "HARMONY_TEST_RESULT total=7 passed=$::passed failed=0"
