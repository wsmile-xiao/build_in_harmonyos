#!/usr/bin/env tclsh
# test_tdbc.tcl — tdbc/1.1.14 消费者测试（Conan test_package）
#
# R34：必须实质调用被测包的 API（不是打印空壳）。
# 另含 2 项鸿蒙特有断言（ohos-platform / ohos-elf-aarch64）。
#
# 说明：tdbc::tokenize 返回**扁平向量** —— [literal var literal var ... literal]
# （无绑定变量时只有 1 个元素），与上游 tests/tokenize.test 的期望一致。

set pass 0
set fail 0

proc check {name script {detail ""}} {
    global pass fail
    # 表达式在全局作用域求值（脚本里用到全局变量/内建数组）
    if {[uplevel #0 [list expr $script]]} {
        incr pass
        puts "++++ $name PASSED $detail"
    } else {
        incr fail
        puts "---- $name FAILED $detail"
    }
}

# 读取 ELF 头，返回 {magic ei_class e_machine}
proc elf_header {path} {
    set fh [open $path rb]
    set data [read $fh 20]
    close $fh
    binary scan $data H8 magic
    binary scan [string range $data 4 4] H2 ei_class
    binary scan [string range $data 18 19] H* machine_hex
    set lo [scan [string range $machine_hex 0 1] %x]
    set hi [scan [string range $machine_hex 2 3] %x]
    return [list $magic $ei_class [expr {$lo + $hi * 256}]]
}

# 1) 包版本
check "tdbc-version" {[package require tdbc] eq "1.1.14"}

# 2) SQL 分词器：绑定变量被分离出来
set tokens [tdbc::tokenize {SELECT * FROM t WHERE a = :b}]
check "tdbc-tokenize-bind" \
    {[llength $tokens] == 2 && [lindex $tokens 1] eq ":b"} "tokens=\{$tokens\}"

# 3) 无绑定变量时只有一个字面量
set plain [tdbc::tokenize {SELECT 'a b' FROM t}]
check "tdbc-tokenize-quoted" {[llength $plain] == 1} "tokens=\{$plain\}"

# 4) 与上游 tokenize-2.0 一致的向量结果
check "tdbc-tokenize-vector" \
    {[tdbc::tokenize {SELECT :a, ':b' FROM y}] eq {{SELECT } :a {, ':b' FROM y}}}

# 5) SQLSTATE 映射（真实调用）
check "tdbc-mapSqlState" {[tdbc::mapSqlState 23505] eq "CONSTRAINT_VIOLATION"} \
    "-> [tdbc::mapSqlState 23505]"

# 6) TclOO 基类命令已注册
set missing {}
foreach cmd {tdbc::connection tdbc::statement tdbc::resultset} {
    if {[llength [info commands $cmd]] == 0} { lappend missing $cmd }
}
check "tdbc-base-classes" {[llength $missing] == 0} "missing=\{$missing\}"

# 7) 动态库确实被 dlopen 加载
set libpath ""
foreach entry [info loaded] {
    lassign $entry path pkg
    if {[string equal $pkg "Tdbc"]} { set libpath $path }
}
check "tdbc-solib-loaded" {[string length $libpath] > 0} "$libpath"

# 8) [鸿蒙特有] 运行平台为 HarmonyOS
check "ohos-platform" {
    [string match -nocase "*harmony*" [exec uname -s]] &&
    [string match -nocase "*harmony*" $tcl_platform(os)]
} "os=$tcl_platform(os) uname=[exec uname -s]"

# 9) [鸿蒙特有] 已加载的 libtdbc1.1.14.so 是 ELF64 / AArch64 产物
if {[string length $libpath] > 0} {
    lassign [elf_header $libpath] magic ei_class machine
    check "ohos-elf-aarch64" \
        {($magic eq "7f454c46") && ($ei_class eq "02") && ($machine == 183)} \
        "magic=$magic class=$ei_class machine=$machine (183=AArch64)"
} else {
    check "ohos-elf-aarch64" 0 "缺少已加载库路径"
}

puts "test_tdbc:\tTotal\t[expr {$pass + $fail}]\tPassed\t$pass\tFailed\t$fail"
if {$fail > 0} {
    exit 1
}
exit 0
