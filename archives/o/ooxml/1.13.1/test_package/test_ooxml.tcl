#!/usr/bin/env tclsh
# test_ooxml.tcl —— ooxml 1.13.1 test_package 消费者用例（只用交付的包）。
#
# 用法: tclsh8.6 test_ooxml.tcl <ooxml package_folder>
# 依赖: 被测包 lib/ooxml1.13.1/（pkgIndex.tcl + ooxml*.tcl）、依赖包 tdom。
# 共 12 项可核对结果，全部通过退出码 0，任一失败退出码 1。

set pkgroot [lindex $argv 0]
if {$pkgroot eq ""} { puts stderr "usage: tclsh test_ooxml.tcl <ooxml package_folder>"; exit 2 }
# auto_path 指向交付的包（L1e 移走 lib/ 后这里必然 package 失败）
lappend auto_path [file join $pkgroot lib ooxml1.13.1]

package require ooxml
package require tdom

set ::n_total 0
set ::n_fail 0
proc check {name body expect} {
  incr ::n_total
  if {[catch {uplevel 1 $body} result]} {
    incr ::n_fail
    puts "FAIL $name: error - $result"
    return
  }
  if {$result ne $expect} {
    incr ::n_fail
    puts "FAIL $name: got {$result}, want {$expect}"
    return
  }
  puts "PASS $name"
}

set workdir [file join [pwd] tp_work]
file delete -force $workdir
file mkdir $workdir
cd $workdir

# ------------------------------------------------------------------ #
# 1. xl_write：生成 xlsx（字符串 + 数值 + 两个 sheet）
# ------------------------------------------------------------------ #
set xlsx [file join $workdir tp.xlsx]
check {1.1 xl_write 生成 xlsx} {
  set s [::ooxml::xl_write new -creator {OHOS Test}]
  set sheet [$s worksheet {Sheet1}]
  $s cell $sheet {hello-ooxml} -index A1
  $s cell $sheet 42 -index A2
  set sheet2 [$s worksheet {Sheet2}]
  $s cell $sheet2 {second} -index B2
  $s write $xlsx
  $s destroy
  expr {[file exists $xlsx] && [file size $xlsx] > 1000}
} 1

# ------------------------------------------------------------------ #
# 2. xl_read：内建 zlib zip 读取器读回并逐项核对
# ------------------------------------------------------------------ #
array set wb [::ooxml::xl_read $xlsx -valuesonly]
check {2.1 xl_read sheet 数量} { llength $wb(sheets) } 2
check {2.2 xl_read Sheet1!A1 字符串} { set wb(0,v,0,0) } {hello-ooxml}
check {2.3 xl_read Sheet1!A2 数值} { set wb(0,v,1,0) } 42
check {2.4 xl_read Sheet2!B2 字符串} { set wb(1,v,1,1) } {second}

# ------------------------------------------------------------------ #
# 3. 数值格式（xl_write 深路径）+ 读回往返
# ------------------------------------------------------------------ #
set fmtxlsx [file join $workdir tp_fmt.xlsx]
check {3.1 xl_write 数值格式（style/numberformat）} {
  set s [::ooxml::xl_write new]
  set sheet [$s worksheet {Fmt}]
  set st [$s style -numfmt [$s numberformat -decimal]]
  $s cell $sheet 3.14159 -index A1 -style $st
  $s write $fmtxlsx
  $s destroy
  expr {[file exists $fmtxlsx] && [file size $fmtxlsx] > 1000}
} 1
check {3.2 xl_read 数值格式往返} {
  array set fmt [::ooxml::xl_read $fmtxlsx -valuesonly]
  expr {abs($fmt(0,v,0,0) - 3.14159) < 1e-9}
} 1

# ------------------------------------------------------------------ #
# 4. docx 导出（tdom XML/DOM 后端 —— 验证 tdom 依赖真实被用上）
# ------------------------------------------------------------------ #
set docxfile [file join $workdir tp.docx]
check {4.1 docx 导出（tdom 后端）} {
  package require ooxml::docx
  set d [::ooxml::docx::docx new -creator {OHOS Test}]
  $d paragraph {Hello from ooxml on OHOS}
  $d write $docxfile
  $d destroy
  expr {[file exists $docxfile] && [file size $docxfile] > 1000}
} 1

# docx 本质是 zip：用 ooxml 内建读取器确认包内关键成员存在
check {4.2 docx 包内成员（word/document.xml）} {
  ::ooxml::ZipOpen $docxfile
  expr {[lsearch -exact [dict keys $::ooxml::zlibcdir] {word/document.xml}] > -1}
} 1
check {4.3 docx 包内成员（[Content_Types].xml）} {
  expr {[lsearch -exact [dict keys $::ooxml::zlibcdir] {[Content_Types].xml}] > -1}
} 1
check {4.4 docx document.xml 内容可解出} {
  expr {[string first {Hello from ooxml on OHOS} [::ooxml::ZlibZipGet word/document.xml]] > -1}
} 1
check {4.5 docx 包内成员数 > 3} {
  expr {[llength [dict keys $::ooxml::zlibcdir]] > 3}
} 1

# ------------------------------------------------------------------ #
# 5. 库 API 形态与错误路径
# ------------------------------------------------------------------ #
check {5.1 package 版本 1.13.1} { package present ooxml } 1.13.1
check {5.2 xl_read 错误路径：非 zip 文件} {
  set junk [file join $workdir junk.xlsx]
  set fd [open $junk w]; puts $fd {not a zip}; close $fd
  catch {::ooxml::xl_read $junk} err
} 1

# 清理与汇总
file delete -force $workdir
puts "----"
puts "consumer-test: total=$::n_total failed=$::n_fail"
if {$::n_fail > 0} { exit 1 }
exit 0
