#!/usr/bin/env tclsh
# ---------------------------------------------------------------------------
# tdom 0.9.6 —— 完整消费者用例（平台 rule12：真跑端到端业务流程）
#
# 只使用交付物：$pkgdir/lib/tdom0.9.6/ 下的 libtdom0.9.6.so + tdom.tcl +
# pkgIndex.tcl。流程覆盖 tdom 的主要业务面：
#   ① package require（经 pkgIndex.tcl 加载 .so 与 Tcl 侧脚本）
#   ② XML 解析（bundled expat）+ DOM 树结构与属性读写
#   ③ XPath 1.0：路径/谓词/函数（count/sum/string/position）
#   ④ DOM 增删改 + 序列化（asXML）与再解析往返一致
#   ⑤ XSLT 1.0 变换
#   ⑥ JSON 解析（dom parse -json）与 DOM 映射
#   ⑦ 大文档上的 XPath 位置谓词（500 节点）
#   ⑧ 错误路径：非法 XML 必须报错
# 结果用显式比对 + 计数 + 退出码表达（不用 assert）。
# ---------------------------------------------------------------------------
if {[llength $argv] < 1} {
    puts "用法: tclsh test_tdom.tcl <package_folder>"
    exit 2
}
set pkgdir [lindex $argv 0]
set teadir [file join $pkgdir lib tdom0.9.6]
lappend auto_path $teadir

set checks 0
set fails 0
# check <标签> <条件表达式> [补充信息]
# 条件在**调用者作用域**里用 expr 求值（花括号传入时不做提前替换，变量照常可见）。
proc check {label cond {detail ""}} {
    global checks fails
    incr checks
    set ok [uplevel 1 [list expr $cond]]
    if {$ok} {
        puts "\[ok  \] $label"
    } else {
        incr fails
        puts "\[FAIL\] $label  $detail"
    }
    flush stdout
}

# ① 加载交付的扩展
set loaded [catch {package require tdom} ver]
check "package require tdom 得到交付版本（得到 '$ver'）" {!$loaded && $ver eq "0.9.6"}
check "交付物含 libtdom0.9.6.so" {[file isfile [file join $teadir libtdom0.9.6.so]]}
check "交付物含 Tcl 侧脚本 tdom.tcl + pkgIndex.tcl" \
      {[file isfile [file join $teadir tdom.tcl]] && [file isfile [file join $teadir pkgIndex.tcl]]}

# ② XML 解析 + DOM 结构/属性
set xml {<?xml version="1.0"?>
<catalog xmlns:dc="http://purl.org/dc/elements/1.1/">
  <book id="b1" lang="en"><title>HarmonyOS</title><price>128</price>
    <dc:creator>OpenHarmony</dc:creator></book>
  <book id="b2" lang="zh"><title>鸿蒙</title><price>64</price>
    <dc:creator>开放原子</dc:creator></book>
</catalog>}
set doc [dom parse $xml]
set root [$doc documentElement]
check "DOM 根节点 nodeName = catalog" {[$root nodeName] eq "catalog"}
check "DOM 根节点有 2 个子元素（得到 [llength [$root childNodes]]）" {[llength [$root childNodes]] == 2}
set b1 [$root selectNodes {/catalog/book[@id='b1']}]
check "属性读取 id/lang 正确（[$b1 getAttribute id]/[$b1 getAttribute lang]）" \
      {[$b1 getAttribute lang] eq "en" && [$b1 getAttribute id] eq "b1"}

# ③ XPath 1.0：谓词 + 函数
set t2 [$root selectNodes {string(/catalog/book[@id='b2']/title)}]
check "XPath 谓词取到第二条书目标题（得到 '$t2'）" {$t2 eq "鸿蒙"}
set n [$root selectNodes {count(/catalog/book)}]
check "XPath count() = 2（得到 $n）" {$n == 2.0}
set total [$root selectNodes {sum(/catalog/book/price)}]
check "XPath sum(price) = 192（得到 $total）" {$total == 192.0}
set creator [$root selectNodes -namespaces {dc http://purl.org/dc/elements/1.1/} {string(//dc:creator[.='开放原子'])}]
check "XPath 命名空间前缀查询（得到 '$creator'）" {$creator eq "开放原子"}

# ④ DOM 增删改 + 序列化往返
set new [$doc createElement book]
$new setAttribute id b3
$new appendChild [$doc createTextNode "第三本"]
$root appendChild $new
set n3 [$root selectNodes {count(/catalog/book)}]
check "追加节点后 count() = 3（得到 $n3）" {$n3 == 3.0}
$new delete
set n2 [$root selectNodes {count(/catalog/book)}]
check "删除节点后 count() 回到 2（得到 $n2）" {$n2 == 2.0}

set text [$doc asXML -indent none]
set doc2 [dom parse $text]
set root2 [$doc2 documentElement]
check "序列化 asXML 后再解析，书目数据一致" \
      {[$root2 selectNodes {string(/catalog/book[@id='b2']/title)}] eq "鸿蒙"}
check "序列化结果长度 > 200（得到 [string length $text]）" {[string length $text] > 200}

# ⑤ XSLT 1.0 变换
set style [dom parse {<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text"/>
  <xsl:template match="/"><xsl:for-each select="//title"><xsl:value-of select="."/>|<xsl:if test="position()!=last()">,</xsl:if></xsl:for-each></xsl:template>
</xsl:stylesheet>}]
set rc_xslt [catch {$root xslt $style resultDoc} err_xslt]
if {$rc_xslt} {
    check "XSLT 变换执行" {0} "$err_xslt"
} else {
    set out [$resultDoc asXML -indent none]
    check "XSLT 变换输出包含两本书标题（得到 '$out'）" \
          {[string match "*HarmonyOS*" $out] && [string match "*鸿蒙*" $out]}
}
$doc delete

# ⑥ JSON 解析与 DOM 映射
set jdoc [dom parse -json {{"name":"tdom","nums":[1,2,3],"nested":{"ok":true}}}]
set jroot [$jdoc documentElement]
set jxml [$jdoc asXML -indent none]
set json_name [$jroot selectNodes {string(//name)} ]
check "JSON 解析后 XPath 能取到 name（得到 '$json_name'）" {$json_name eq "tdom"}
check "JSON → DOM 序列化含键名（得到 '$jxml'）" \
      {[string match "*tdom*" $jxml] && [string match "*nested*" $jxml]}
$jdoc delete

# ⑦ 大文档上的 XPath 位置谓词
set big [dom createDocument bigdoc]
set broot [$big documentElement]
for {set i 1} {$i <= 500} {incr i} {
    set item [$big createElement item]
    $item setAttribute idx $i
    $item appendChild [$big createTextNode "n$i"]
    $broot appendChild $item
}
check "大文档 500 个节点" {[$broot selectNodes {count(/bigdoc/item)}] == 500.0}
check "XPath 位置谓词 position() mod 100 命中 5 个" \
      {[$broot selectNodes {count(/bigdoc/item[position() mod 100 = 0])}] == 5.0}
check "XPath 按属性取第 250 个节点文本" \
      {[$broot selectNodes {string(/bigdoc/item[@idx='250'])}] eq "n250"}
$big delete

# ⑧ 错误路径
set rc_bad [catch {dom parse {<a><b></a>}} err_bad]
check "非法 XML 解析必须报错（得到 rc=$rc_bad）" \
      {$rc_bad != 0 && [string length $err_bad] > 0}

puts ""
puts "tdom 消费者用例结果：$checks 项检查，$fails 项失败"
if {$fails} {
    exit 1
}
exit 0
