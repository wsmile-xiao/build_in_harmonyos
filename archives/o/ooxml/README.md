# ooxml

## 简介
ooxml 是 Alexander Schoepe 维护的**纯 Tcl** 扩展包，用于读写 Office Open XML
文件：把 Tcl 数组导出成 Excel `.xlsx`（`::ooxml::xl_write` / `xl_read` /
`tablelist_to_xl`），并通过 `::ooxml::docx` 导出 Word `.docx`。

上游：https://fossil.sowaswie.de/ooxml/ （Fossil 仓库）

## OHOS 适配要点
- 纯 Tcl 包，无 C 源码、无编译产物：交付 TEA 布局的 `lib/ooxml1.13.1/`
  （`ooxml.tcl` + `ooxml-docx*.tcl` + `pkgIndex.tcl`），由 tclsh 在运行时
  `package require ooxml` 加载；`pkgIndex.tcl` 由 `pkgIndex.tcl.in` 模板替换生成
- 依赖 `tcl/8.6.16`（tclsh8.6 运行时与 tcltest 测试框架）、`tdom/0.9.6`
  （docx 写入路径的 XML/DOM 后端），均已在仓库制品仓发布
- 读 `.xlsx` 优先使用 ooxml 内建的 zlib zip 读取器（Tcl 8.6 核心 `[zlib]` 命令），
  不需要 tclvfs / tcllib；上游 `tests/` 中两处假定 tclvfs 的用例以**测试补丁**
  补齐 `zipAccessMethod == "zlib"` 分支（见 `patches/`，仅 tests/ 文件）
- 上游测试套件的 docProps 时间戳用例把期望值硬编码为维护者时区
  （Europe/Berlin +01）的换算结果，运行测试时显式设置 `TZ=Europe/Berlin`
  忠实复现上游预期（不改测试内容）

## 使用（Tcl 消费者）
```tcl
lappend auto_path <ooxml_pkg>/lib/ooxml1.13.1   ;# 或把 OOXML_TCL_DIR 加进 auto_path
package require ooxml
set s [::ooxml::xl_write new]
set sheet [$s worksheet {Sheet1}]
$s cell $sheet {hello} -index A1
$s write out.xlsx
$s destroy
```

## 版本
- 1.13.1：首次适配（上游测试 626 用例：Passed 617 / Skipped 9 / Failed 0）
