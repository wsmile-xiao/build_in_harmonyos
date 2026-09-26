# jimtcl 0.83 test_package — consumer view: drive the packaged jimsh binary.
# Executed by <package>/bin/jimsh (test_package/conanfile.py test()).
# Every assertion counts towards the "鸿蒙特有测试" row of the PR body.

set checks 0
set failures 0

proc ck {desc got want} {
    global checks failures
    incr checks
    if {$got eq $want} {
        puts "PASS\[$checks\] $desc"
    } else {
        incr failures
        puts "FAIL\[$checks\] $desc: got '$got' want '$want'"
    }
}

ck "jimsh reports packaged version" [info patchlevel] "0.83"
ck "expr arithmetic" [expr {2+3*4}] "14"
ck "string functions" [string toupper jimtcl] "JIMTCL"
ck "dict functions" [dict get {platform ohos} platform] "ohos"
ck "zlib extension roundtrip" [zlib inflate [zlib deflate "harmonyos-pc"]] "harmonyos-pc"

puts "jimsh.tcl: [expr {$checks - $failures}]/$checks assertions passed"
if {$failures} {
    exit 1
}
exit 0
