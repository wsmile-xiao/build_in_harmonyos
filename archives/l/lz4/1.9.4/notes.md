# lz4 1.9.4 — 编译进度

> 档案创建时间: 2026-09-03
> 最后更新: 2026-09-03
> 当前状态: success

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lz4 |
| 版本 | 1.9.4 |
| 状态 | ✅ success |
| 构建系统 | makefile |
| 源码 | https://github.com/lz4/lz4/archive/refs/tags/v1.9.4.tar.gz |

## 二、编译阶段
- [x] conan create 构建通过（lz4/1.9.4）
- [x] test_package 消费测试通过（LZ4_compress_default + LZ4_decompress_safe 往返）
- [x] 上游测试全量执行（23 个可执行目标全部 PASS；8 个宿主硬缺目标如实记录，见 reports/upstream-test-report.md）

## 三、适配要点（知识沉淀）
1. **OHOS `/bin/sh` 受限**：make 默认用 `/bin/sh`，OHOS 下不可访问（`Permission denied`）。构建必须显式传 `SHELL=/data/service/hnp/bin/bash`。
2. **无 `cc` 默认编译器**：lz4 Makefile 未硬编码 `CC`，依赖 make 内置 `cc`，OHOS 工具链无此名。需传 `CC=clang CXX=clang++`。
3. **hmdfs 不支持符号链接**：动态库 versioned links（`ln -sf liblz4.so.1.9.4 liblz4.so.1`）在 hmdfs 下失败（`Permission denied`）。传 `LN_SF=cp` 以复制替代（对应知识 E050 copy-replace-symlink）。
4. **1.9.4 无顶层 `lib-shared` 目标**（与 1.10.0 不同），共享库需在 `lib/` 目录 make。
5. **test_package 避免 CMake**：OHOS 下 CMakeToolchain 生成的 makefile 内部用 `/bin/sh` 会失败，改用 clang 直接编译 + bash 运行（参考 zstd test_package 思路）。
6. **依赖别名**：lz4c/unlz4/lz4cat 由 `LN_SF` 生成，使用 `LN_SF=cp` 避免符号链接。
7. **测试补丁（修上游测试平台缺陷/适配）**：
   - `0002-freestanding.patch`：`freestanding.c` 非 x86_64 分支 `_start` 为空 `ret`（无退出机制），OHOS aarch64 下 `./freestanding` 段错误。补丁加入 exit 系统调用使 `_start` 正常退出 → test-freestanding 通过（经反汇编确认上游缺陷）。
   - `0003-test-install.patch`：`test_install.sh` 的 `make` 不带 `POSIX_ENV=Yes`（顶层 install 目标仅在 `ifeq ($(POSIX_ENV),Yes)` 下定义），HarmonyOS uname 不匹配 Linux/BSD 且 Makefile 硬赋值 POSIX_ENV → install 目标空壳。补丁让 make 带 `POSIX_ENV=Yes`+`SHELL`+`CC`+`LN_SF=cp` 适配 → test_install.sh 逻辑通过（bash 直属运行 SAME!/EMPTY!）。
8. **conan build() 不跑 make check**：OHOS conan `self.run` 环境管道受限（`cat|` 报 `standard output: Permission denied`）+ hmdfs 别名覆盖限制（`cp: unlz4 Operation not permitted`），上游测试普遍含管道，故沿用已发布库（lz4 1.10.0/zstd/snappy）做法——build() 仅构建，CI L1 走 test_package。

## 四、上游测试执行
- **可执行目标 23 个全部通过 (23/23 = 100%)**（含补丁修复后通过的 test-freestanding、test-install；frametest 1237/1237）。
- **全量通过率 23/31 (74.19%)**：另有 **8 个宿主硬缺目标**因 OHOS 缺工具链/依赖无法执行（非 lz4 缺陷）——32 位变体（test-frametest32/fullbench32/fuzzer32/lz4c32/lz4c32-basic/mem32，缺 -m32）、test-interop-32-64（缺 lz4c32 32位 loader）、test-mem（缺 valgrind）。详见 reports/upstream-test-report.md。

## 五、结束记录
- **最终状态**: success
- **结束时间**: 2026-09-03
---

**编译结束**: 2026-09-03 22:46
**最终状态**: built
