# jpegpixi 1.1.1 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.59 / automake 1.9，tarball 自带预生成 configure 与 Makefile.in）
- 编译日期: 2026-09-25
- 编译器: clang (OpenHarmony SDK)
- 状态: built

## 上游测试清点（R51 三步法）
- 清点证据：tarball 顶层无 tests/ 目录；Makefile.am 无 TESTS 变量、无自定义 check 规则（automake gnu 默认 check 目标注册的测试数为 0）；po/ 仅翻译模板非测试。
- 结论：上游无自动化测试面 → 消费侧真实执行冒烟（test_package/test.sh，7 断言，全部套 timeout(1)）。

## 编译步骤

1. `bash ci/scripts/preflight_check.sh jpegpixi/1.1.1` — W0 依赖核验（libjpeg/10 已发布）
2. `python3 scripts/ohc-run.py recipe-search jpegpixi` — 无相似配方（语料 6173 条），走 conanfile-autotools 模板 + 同族先例 aaphoto/0.45（autotools + libjpeg/10 CLI）
3. `python3 scripts/ohc-run.py build jpegpixi 1.1.1` — conan create 一键构建
4. `python3 scripts/ohc-run.py conan-verify jpegpixi 1.1.1` — 八门禁
5. `python3 scripts/ohc-run.py finish jpegpixi 1.1.1 built`

## 关键适配点

| # | 症状/风险 | 根因 | 方案 |
|---|-----------|------|------|
| 1 | configure 探测不到 libjpeg | acinclude.m4 自定义 MD_PATH 宏探测 jpeglib.h + -ljpeg（jpeg_start_decompress），无 conan 依赖时必失败 | conanfile requirements 声明 `libjpeg/10`，generate() 用 AutotoolsDeps 注入 -I/-L/-l（R49 合规，无 /usr 路径） |
| 2 | make 可能调用缺失的 `opag` 生成器 | optpixi.c/opthotp.c 由 BUILT_SOURCES 规则从 .opag 生成，configure 只找到 `missing` | 无需处理：tar 内 mtime 已保证 .opag（04:24/04:30）旧于生成物（04:40；04:24 为审计独立解包实测），make 不触发重建（实测验证） |
| 3 | gettext/libintl 缺失告警 | MD_NLS 宏在 OHOS 上找不到 NLS 支撑会 WARN 降级 | configure_args 显式 `--disable-nls` |
| 4 | HMDFS 并行 make jobserver EPERM | E074 | autotools.make(args=["-j1"]) |
| 5 | /usr 硬编码路径 | 任务提示待定位 | 实测 configure 内 /usr 均为 autoconf 2.59 标准样板（as_dir 搜索路径、ac_default_prefix、oldincludedir），无危险硬编码，无需补丁 |

## K0 合规情况
- 主命令 `jpegpixi` 与包名一致，无需包装入口。
- CLI 为 GNU 风格（optpixi.c 由 opag 生成，用法行 `Usage: %s [OPTION]... SOURCE DEST [[D:]X,Y[,S]|[,SX,SY]]...`）。
- **实测：`jpegpixi --help` rc=0**（conan-verify L2 smoke 与 test.sh 双确认），K0 通过；未测 `--version`（test.sh 的 help→version 回退未触发）。
- 上游语法如实探针：单点 `X,Y` 与块 `X,Y,S` 两种坐标形式均作为真实断言；未假设未在源码中出现的旗标。

## 测试五维账本（实测于 conan-verify G2/L2）
- 静态清点：上游 0 个测试（tarball 无 tests/、Makefile.am 无 TESTS）
- 可执行：test_package/test.sh 7 断言（K0 探针、单点修复、SOI/EOI、块修复、SOF 尺寸保持、往返重解析、输入生成）
- 通过 7 / 跳过 0 / 失败 0 —— `[result] PASS=7 FAIL=0`（证据：reports/conan-create.log；.ci-result.json integrity_hash 由 finish 写入）

## 路径 B 声明（3+2）
- 适配路径：路径 A（直接适配）+ 路径 B 判定 = hit（同族先例复用——aaphoto/0.45 的 autotools + libjpeg/10 + AutotoolsDeps 注入骨架，经本包源码实测裁剪；无新增机制）
- 使用知识库：aaphoto/0.45 配方（libjpeg/10 依赖注入与 LD_LIBRARY_PATH 兜底）；E074（-j1 绕 HMDFS jobserver）；K0（CLI --help/--version 探针规范）；R49（依赖注入合规形态）
- 知识库扩展：本次未发现新错误模式（构建如出现新失败将按 R31 自动生成 DRAFT 草稿并回填本节）
- 关联 Issue：无需（B 判定 = hit ⇒ 不建【知识库扩展】Issue；路径 C 未申请，无【高难度挑战】Issue）
---

**编译结束**: 2026-09-25 04:01
**最终状态**: built
**CIW-B2 整改记录（2026-09-27）**: Septest rule1+rule4 判「复选框解析不到 + 编译状态字段缺失(None)」，病根=①复选框在 ### 小节内（解析器只认 ## 节直属，CIW-F2 ①类细则）；②编译状态/通过率三行放在「测试用例对比」节而解析器只扫「验证结果」节。已将复选框两节改为「- **问题** + 复选框」格式、三个统计行搬入「验证结果」节首，正文已 PATCH。本提交仅刷 HEAD 绑新判决（同 HEAD 重提复用旧 FAIL 教训），零功能性改动。
