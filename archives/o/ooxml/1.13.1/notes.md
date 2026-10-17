# ooxml 1.13.1 适配笔记

## 编译环境
- 构建系统: none（纯 Tcl 包，无编译；脚本安装进 TEA 布局）
- 编译日期: 2026-10-04
- 运行时: tcl/8.6.16（tclsh8.6，aarch64 鸿蒙PC 原生）+ tdom/0.9.6
- 状态: published

## 适配步骤（无编译）

1. `conan source`：从上游 Fossil 仓库 tag `version-1.13.1` 拉取 tar.gz（官方源，
   sha256 `ee6c87c4e564c2ca76640022dfcabacef9c29658bc7996532a21297cd0712809`）。
2. `conandata.yml` 声明两处 tests/ 测试补丁（见下）。
3. `build()`：用交付链 tclsh8.6 + TCLLIBPATH(tdom) 真跑上游 `tests/all.tcl`
   （tcltest，29 个测试文件），解析汇总行，Failed≠0 构建失败。
4. `package()`：收集 4 个运行期脚本 + 替换生成的 `pkgIndex.tcl` 到
   `lib/ooxml1.13.1/`（TEA 布局），`license.terms` 到 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xlsx-formula.test 整文件报错退出（0 用例执行） | 第 21 行对 Tcl<9 硬性 `package require vfs::zip`，环境无 tclvfs | 测试补丁 0001：容错加载，无 tclvfs 回落内建 zlib zip 读取器 |
| 2 | xlsx-simple.test 中 MountXLSX-2.1 失败 → `appDoc` 未定义 → 文件级错误连锁 | else 分支（Tcl9/tcllib 之外）假定 tclvfs 存在 | 测试补丁 0002：补齐 `zipAccessMethod=="zlib"` 分支（ZipOpen/ZlibZipGet/清理分支），有 tclvfs 时行为不变 |
| 3 | DocPropsCore-4.4/4.5 时间戳差 7~8 小时 | 上游把期望值按维护者时区（Europe/Berlin，10 月底已回 +01）硬编码 | 运行测试时显式 `TZ=Europe/Berlin`（已实测 zoneinfo 可用），不改测试期望 |
| 4 | `ZlibZipGet xlsx/docProps/app.xml` 报 key 不存在 | vfs/zipfs 方案把归档挂载在 `xlsx` 前缀下，归档内真实成员名是 `docProps/...` | 测试补丁 0002 中用归档内真实成员路径 |

## 上游测试（R51 三步法）

- 清点：`tests/` 29 个 `.test` 文件 + `all.tcl`（tcltest 驱动）。
- 运行：本机 aarch64 真机原生 tclsh8.6（来自已发布的 tcl/8.6.16 包）实跑
  `TCL_LIBRARY=<tcl>/lib/tcl8.6 TCLLIBPATH=<tdom>/lib/tdom0.9.6 TZ=Europe/Berlin
  tclsh8.6 tests/all.tcl -load "package ifneeded ooxml 1.13.1 [...]"`。
- 结果：**all.tcl: Total 626 Passed 617 Skipped 9 Failed 0**（通过率 100%，
  9 个 skip 全部为 `mutation` 约束——tcltest 变异测试约束，环境不提供变异工具）。

## 源码修改（补丁）

- `patches/0001-tests-xlsx-formula.test.patch`（+3/-1，测试）
- `patches/0002-tests-xlsx-simple.test.patch`（+18/-4，测试）

均为 tests/ 测试文件，不涉及平台宏、不涉及库代码；有 tclvfs 的环境走原路径不变。

## 依赖版本

- tcl/8.6.16（已发布，提供 tclsh8.6 与 tcltest；ooxml 要求 Tcl >= 8.6.7）
- tdom/0.9.6（已发布，docx 写入路径要求 tdom >= 0.9.6）

## 验证结果

```text
conan create（W3 本地 CI 同款）：conan-verify 8 道门禁通过
上游测试: Total 626 Passed 617 Skipped 9 Failed 0
test_package 消费者用例: 12 项全过（xl_write→xl_read 往返、数值格式、docx(tdom)、错误路径）
交付形态自检: test_layout.py 12 项全过
```

## 注意事项

- 纯 Tcl 包无 C/C++ 链接产物：`cpp_info.libs=[]`，无 `bin/` → 无 commands.json 义务（R38）。
- 消费者把 `OOXML_TCL_DIR`（runenv 提供）加进 `auto_path` 后 `package require ooxml`。
- pkgIndex.tcl 由模板替换生成，避免为它跑整套 TEA configure。
---

**编译结束**: 2026-10-04 08:03
**最终状态**: built
