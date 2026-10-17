# tdom

**tDOM — Tcl 的 XML/DOM/XPath/XSLT/JSON 扩展**（纯 C，TEA 扩展），
上游：<http://tdom.org>，许可证 MPL-2.0。

```tcl
lappend auto_path /path/to/package/lib/tdom0.9.6
package require tdom
set doc [dom parse {<catalog><book id="b1"><title>HarmonyOS</title></book></catalog>}]
set root [$doc documentElement]
puts [$root selectNodes {string(/catalog/book[@id='b1']/title)}]   ;# HarmonyOS
```

本包交付 TEA 布局：`lib/tdom0.9.6/{libtdom0.9.6.so, libtdomstub0.9.6.a, tdom.tcl,
pkgIndex.tcl}` + `include/tdom.h` + `lib/tdomConfig.sh` + `licenses/LICENSE`，
唯一依赖是已发布的 `tcl/8.6.16`。

测试：上游 tcltest 套件（`make check`，2459 例 / 0 失败）在 build() 内真跑；
完整消费者用例（21 项端到端业务流程）与 17 项交付形态自检见 `notes.md`。
