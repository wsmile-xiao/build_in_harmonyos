# rampler 2.1.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists：find_package(QUIET) 优先 + FetchContent 兜底）
- 编译日期: {2026-09-30}
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. conandata 源取官方 tag 归档（codeload 2.1.1，sha256 见 conandata.yml）。
2. `self.requires("bioparser/3.0.15")` + `self.requires("biosoup/0.10.0")`（两者均已在
   ohpcd 远端发布）+ CMakeDeps——上游 CMakeLists 对两依赖先 `find_package(<pkg> <ver> QUIET)`，
   命中即不触发 FetchContent 的 git clone，**空子模块 vendor/bioparser/ 不再被触碰**。
3. `cmake.configure()` + `cmake.build()`；install 走上游 `install(TARGETS rampler ...)`。
4. CLI 行为实测：`--version` → "2.1.1"（rc=0）；无参数 → usage（rc=0，非错误）；
   `-o .`（有选项无位置参数）→ `[rampler::] error: missing arguments!`（rc=1 确定性早退）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 新 CONAN_HOME 缺 extensions/profiles 骨架 → `The 'profile.py' plugin file doesn't exist` | cp 三个文件建 home 不完整 | 从可用 home 复制 extensions/、migrations/、profiles/ 骨架 |
| 2 | source() 下载超时：conandata 被驱动改写为 ghfast.top 镜像且该镜像 read-timeout | 镜像不可达 | 用 `core.sources:download_cache`（共享 dlcache）按 sha256 种入源码 + json 边车（references 含原始/镜像两 URL） |
| 3 | test_package 首版断言 `rampler -v` 报 unrecognized option | getopt 串只有 "o:h"，版本选项是长选项 `--version` | 先实机跑一次拿真实行为再写断言；无参数走 usage(rc=0)，`-o .` 才触发 missing arguments |

## 源码修改

零补丁：上游源码未改动（M2 的空子模块经由 find_package 命中 conan 包被自然绕过）。

## 依赖版本

- bioparser/3.0.15（已发布，ohpcd 远端）
- biosoup/0.10.0（已发布，ohpcd 远端）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify rampler 2.1.1
# G0-G4 全部 PASS（milestone=conan_verify_passed）
# test_package 三条断言：--version 输出 2.1.1；`-o .` 输出 missing arguments；
# 无参数输出 usage —— 均通过（真实执行打包产物）。
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/rampler | ≈1 MB | 已签名主二进制（FASTA/Q 子采样/切分工具） |

## 注意事项

1. 空子模块经 find_package 命中已发布依赖被自然绕过（见 B 草稿），vendor/ 目录在产物构建中不参与。
2. 新 CONAN_HOME 三件骨架（extensions/migrations/profiles）与共享 dlcache 配置是本次踩坑的两个环境项，见 manifest knowledge_gained。
3. rampler 的 CLI：无参数走 usage（rc=0）； 触发 missing arguments（rc=1）——消费者测试按实测断言。
---

**编译结束**: 2026-10-01 08:07
**最终状态**: built
