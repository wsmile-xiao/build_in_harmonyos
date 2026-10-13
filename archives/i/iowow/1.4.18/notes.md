# iowow 1.4.18 适配笔记

## 编译环境
- 构建系统: CMake（顶层 CMakeLists.txt，cmake_minimum_required 3.12；与 1.5.x 的 Autark 不同）
- 编译日期: 2026-10-09
- 编译器: clang 15.0.4（/storage/Users/currentUser/usr/local/bin/clang，aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

1. 官方源码：GitHub Softmotions/iowow tag **v1.4.18**（tar.gz，SHA-256
   `ef4ee56dd77ce326fff25b6f41e7d78303322cca3f11cf5683ce9abfda34faf9` 核验通过；
   注意 plain `1.4.18` tag 返回 404，必须用 v- 前缀 tag）。
2. native 验证（temp/iowow-1.4.18）：CMake 配置
   `-DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON`，
   81/81 目标构建成功，产出 libiowow-1.a + 24 个测试可执行文件。
3. 上游测试：`ctest --output-on-failure` → **23/23 执行器全 PASS**（CUnit 口径
   76 用例 / 13,871,232 断言，0 FAIL 0 SKIP；详见 reports/test-report.md）。
4. Conan 配方（CMake 模板路线，CMakeToolchain + cmake_layout）：
   - `tc.variables` 显式 BUILD_SHARED_LIBS/BUILD_EXAMPLES/BUILD_TESTS/BUILD_BENCHMARKS=OFF；
   - R33：编译器经 CMakeToolchain 从 profile conf `tools.build:compiler_executables`
     注入（profile 原指向 /data/service/hnp/bin/clang 在本机不存在，已修正为
     /storage/Users/currentUser/usr/local/bin/clang）；
   - package_info：libs=["iowow-1"]（实际产物名），system_libs=["pthread","m"]
     （configure 输出 `iowow LINK LIBS: -lpthread;-lm`）。
5. test_package：iwkv 全生命周期 30 项断言（创建/写入/读取/覆盖更新/
   IWKV_NO_OVERWRITE/IWKV_SYNC 落盘/游标遍历/删除/关闭重开持久化），
   `conan create` 内消费者构建运行 30/30 PASS。
6. 鸿蒙专项测试：tests/ 两件套
   - harmonyos_test.c：平台能力（mmap/flock/fsync/pthread+C11 原子/
     CLOCK_MONOTONIC）+ 存储引擎全生命周期，46 项检查；
   - run_ohos_test.sh：T1-T5 共 12 项检查（ELF64/AArch64/musl 纯净/
     无 RPATH/无宿主路径泄漏/真实编译链接运行最终产物）。
   全部 PASS（详见 reports/test-report.md）。
7. conan-verify 8 门禁全部 PASS（G0-G4、L2、L4、L5）。
8. finish published：W2 结构、R36 依赖、W3 本地 CI（.ci-result.json 写入）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 `clang is not a full path to an existing compiler tool` | profile `tools.build:compiler_executables` 指向 /data/service/hnp/bin/clang，本机该路径只有 git 工具 | 修正 profile 为本机真实包装器 /storage/Users/currentUser/usr/local/bin/clang（clang-15 + OHOS sysroot + lld + code-sign） |
| 2 | test_package 断言 `cursor starts at smallest key` 失败 | 1.4.18 块链游标语义与直觉相反：BEFORE_FIRST+NEXT 为**降序**，AFTER_LAST+PREV 为**升序**（iwkv_test1.c L527-539 上游期望 NEXT 首条为最大键证实） | test.c 游标遍历改为 AFTER_LAST+PREV（升序），30/30 PASS；不改库源码 |
| 3 | OHOS 专项 T4 检出静态库含 `/storage/Users/.../src/utils/iwstw.c` 绝对路径 | 上游 IWLOG 宏用 `__FILE__`，CMake 以绝对路径编译源文件，宏展开固化进 rodata | 配方 build() 注入 `-DCMAKE_C_FLAGS=-ffile-prefix-map=<src>=/iowow-src`（上游 CMakeLists 追加式 set 不覆盖），泄漏清零且构建可重现 |
| 4 | harmonyos_test.c 编译错 `iwp_random_fill: too few arguments` | 1.4.18 签名 `iwp_random_fill(char*, int, bool)`（3 参数，ascii 开关） | 补第三参数，顺带覆盖 ascii=true/false 两分支 |
| 5 | 上游测试 cunit 依赖缺失（native 构建期） | 上游 FindCUnit 走 pkg-config | `conan install cunit/2.1.3 -r=ohpcd` + PKG_CONFIG_PATH 指向缓存（1.5.2 同法） |
| 6 | `qsort_r` try_compile 探针失败（构建期） | OHOS musl 无 glibc 风格 qsort_r | 预期失败非库失败：探针不置 HAVE_QSORT_R，iowow 回退自带 sort_r.h（免补丁） |

## 源码修改
- 无补丁（patches/ 为空）。唯一配方级定制是 `CMAKE_C_FLAGS` 追加
  `-ffile-prefix-map`（构建卫生，通用选项，无平台条件）。
- 源码/patch 无 `__OHOS__` 等平台宏：平台能力（qsort_r/clock_gettime/
  pthread/stdatomic/stdbool 等）全走 CMake capability detection。

## 依赖版本
- 构建期测试依赖：cunit/2.1.3（ohpcd 制品仓，仅上游测试单独运行时需要；
  CI 配方 build() 不引入）。
- 运行时仅系统库：pthread、m。

## 验证结果

```bash
# 上游测试全量（23/23 执行器，76 用例，13.87M 断言，0 FAIL 0 SKIP）
cd build-ohos && ctest --output-on-failure          # exit 0
# test_package 消费者（30/30）
conan create archives/i/iowow/1.4.18 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable     # exit 0
# 鸿蒙专项（12/12 + 46 项运行时检查）
sh archives/i/iowow/1.4.18/tests/run_ohos_test.sh <conan pkg prefix> <workdir>  # exit 0
# 配方验证 8 门禁
ohc-run.py conan-verify iowow 1.4.18                # exit 0
# finish
ohc-run.py finish iowow 1.4.18 published
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 构建配方（CMakeToolchain + prefix-map 构建卫生） |
| conandata.yml | 官方源码 URL（v1.4.18 tag）+ SHA-256 |
| test_package/ | 消费者用例（iwkv 全生命周期 30 断言）+ MANIFEST.yml |
| tests/harmonyos_test.c | 鸿蒙专项 C 用例（平台能力 + 存储引擎，46 检查） |
| tests/run_ohos_test.sh | 鸿蒙专项自包含脚本（ELF/musl/RPATH/泄漏/真实运行，12 检查） |
| reports/test-report.md | 上游测试枚举台账 + 双口径统计（23/23） |
| reports/knowledge-ledger.md | 知识候选台账 + 七轴查重 + 路径决定 |
| manifest.yaml | 版本级 manifest（ARCHIVE-SPEC v2.0） |

## 注意事项
- 纯库包（libiowow-1.a），无 CLI 可执行产物，不需要 commands.json（R38 豁免）。
- 游标语义陷阱：1.4.x 与 1.5.x 遍历方向相反，消费者代码从 1.5.x 迁移到
  1.4.x 时游标方向断言须反转（AFTER_LAST+PREV 才是升序）。
- 上游 .pc 文件 `-liowow` 是笔误，真实产物 `-liowow-1`（package_info 已按
  实际产物处理；CMakeDeps 消费者用 `iowow::iowow` target 不受影响）。
- CI 构建 profile 的 compiler_executables 路径是环境特定项，跨 worker 迁移
  时需按机器实际工具链路径修正（本次已修正）。
---

**编译结束**: 2026-10-09 18:31
**最终状态**: published
