# mrboom 5.5 适配笔记

## 编译环境
- 构建系统: makefile（libretro 核心通用 Makefile，`make platform=unix`）
- 编译日期: 2026-09-20
- 编译器: OHOS clang/clang++ 15（profile tools.build:compiler_executables 注入，命令行覆盖 CC/CXX/AR）
- 状态: built

## 编译步骤

1. conandata.yml 指向官方 release 资产 MrBoom-src-5.5.tar.gz
   （github auto-archive 不含 libretro-common 子模块，官方 src release 已内嵌，sha256 c37c09c3…）。
2. build(): `make -C <source> platform=unix SKIP_GIT=1 CC=… CXX=… AR=… -j1`
   产出插件形态共享库 mrboom_libretro.so（link.T 版本脚本仅导出 retro_* ABI）。
3. package(): 拷贝 `*_libretro.so` 至 lib/、LICENSE 至 licenses/；cpp_info.libs 置空
   （libretro 核心由前端 dlopen 加载，无链接语义）。
4. 消费者测试 test_core.c：dlopen 打包产物，断言 retro_api_version()==1、
   system_info 静态元数据（library_name=="Mr.Boom"）、set_environment→init→deinit 生命周期。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github auto-archive（codeload tag 归档）内 libretro-common 为空目录 | 归档不含 git 子模块 | 改用官方 release 资产 MrBoom-src-5.5.tar.gz（已内嵌子模块内容，505 文件） |
| 2 | `No targets specified and no makefile found` | conan basic_layout 构建目录与源码目录分离，make 在空目录执行 | make 加 `-C {source_folder}`（本包 Makefile 仅支持 in-source） |
| 3 | 产物无法执行：`inaccessible or not found` | 新机 HMDFS 继承 umask 007，新文件默认 660 无执行位 | 执行前 `chmod +x`（新机 chmod 生效，旧机 E046 口径不适用，见知识草稿 E543） |
| 4 | E017 ghfast.top 镜像超时导致 source() 失败 | worker 出网对镜像站不稳定 | 共享下载缓存预置官方 tarball（sidecar 同时登记官方与镜像 URL） |

## 源码修改

无补丁（patches 为空）。构建系统级参数（platform=unix/SKIP_GIT/编译器覆盖）均经配方 build() 传入，未改动上游文件。

## 依赖版本

无外部依赖（libretro-common 头文件/实现随官方源码发布）。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify mrboom 5.5
# G0-G4 全 PASS；test_package: ALL CHECKS PASSED（10/10 断言）
python3 scripts/ohc-run.py finish mrboom 5.5 built
# W3 本地 CI 模拟通过（reports/w3-local-ci.log）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/mrboom_libretro.so | 80,320 B | libretro 游戏核心（dlopen 插件） |
| packaging/mrboom-5.5-ohos-aarch64.tar.gz | 8,866,653 B | 打包产物 |

## 测试账本（五维）

- N_static = 0（上游无测试套件：源码树无 test 目录、Makefile 无 check/test 目标、
  CI 配置仅交叉编译；`mrboomTest` 目标为游戏本体非测试，证据见 reports/test-report.md）
- N_registered = 0；N_executed = 0；未执行分类 = 0
- N_consumer = 1（test_core.c，10 项断言全过）

## 路径 B 判断（2026-09-20，GLM-65）

判定：**走 A+B**。新知识：新机 HMDFS umask 007 导致构建产物默认 660 不可执行，
`chmod +x` 在新机生效（推翻旧机 E046"chmod 被忽略"口径）——跨仓库复用（所有需执行
构建产物的包都受影响），知识图谱查重无高相似条目（draft-review 建议 create）。
草稿：knowledge/drafts/E543-draft-6E1A.kv/.md（PR 中单列路径 B 贡献说明，早于 PR 创建
的查重结论与触发实例见本节；PR 编号建好后回填）。

## 注意事项

- 本包为归档树首个 libretro 核心：配方模式（插件 .so、cpp_info.libs 置空、dlopen 消费者测试）可作后续 libretro 系包底稿。
- mrboomTest/mrboom 目标为游戏可执行文件（需 SDL），conan 包仅交付核心 .so，不含独立可执行文件。
---

**编译结束**: 2026-09-20 02:50
**最终状态**: built
