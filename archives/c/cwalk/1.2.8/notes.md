# cwalk 1.2.8 HarmonyOS PC adaptation

## Upstream

- Repository: https://github.com/likle/cwalk
- Tag: `v1.2.8`
- Commit: `88c9c59586f24aa792ff2e2eff49f593f3a0dfa6`
- License: MIT
- Language: C11
- Third-party dependencies: none
- Source sha256: `48b99bd46f0b9ce027ca882b003e44a5db0369dec6fd9898fd5420aa282d780f`
  （GitHub 直连超时，经 gh-proxy 镜像取得后按 sha256 与登记表前缀 `48b99bd46f0b9ce0` 双重核验；
  conandata.yml 保留官方 URL，同 SHA 已预置双机 dlcache `s/<sha256>`，无 sidecar 按“元数据缺失不强制重下”直接命中）

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-23
- 主机: B 机（鸿蒙 PC 工具机），HarmonyOS HongMeng Kernel 1.12.0 aarch64
- 编译器: clang 15.0.4 / cmake 4.1.2 / GNU Make 4.4.1
- conan: 2.29.1（OHOS 适配版，`default_settings.py` md5 `7c7b8229d2ad407390c5980ad17035c7`，与 A 机逐字节同源）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libc++, C++17）
- 状态: built

## 编译步骤

1. `preflight_check.sh cwalk/1.2.8` — 无外部依赖，rc=0
2. `init-build --url=<官方 tarball URL>` — tarball 已预置跳过下载，sha256 校验通过
3. 14 步 driver：cmake configure（`BUILD_SHARED_LIBS=OFF ENABLE_TESTS=ON`）→ build → staging 验证 → conan 配方生成
4. `conan-verify`（G0-G4 + L2/L4/L5 全 PASS）：`conan create` 干净重建 + ctest 180 条 + 消费者测试
5. `finish ... built`（W3 本地 CI 模拟 = setup.sh + build_and_test.sh 同源复跑）

配方以归档 `archives/c/cwalk/1.2.9/`（已过 CI）为底稿移植：版本/sha 改 1.2.8，
补 G1 要求的 `export_sources()`/`apply_conandata_patches()`；无源码补丁。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 FAIL `conandata.yml sha256 未填写` | `conan-init` 阶段 `conandata.yml 模板不可用` 跳过，落了占位符 `REPLACE_WITH_ACTUAL_SHA256`；manifest 同样残留 `{software}`/`{BUILD_SYSTEM}` 占位符与空 sha256 | 填实测 sha256，manifest 占位符清零（占位符残留门 grep 强制） |
| 2 | 生成的 test_package 只打印 "OK" 不调 API | `conan-init` 落的是通用桩模板 | 移植 1.2.9 归档 test_package（1 程序 / 8 断言，API 8/8 命中 1.2.8 头文件） |
| 3 | driver Step7 `make -C build check` 报 `No rule to make target 'check'` → test-report FAIL RC 2 | driver 对 cmake 分支硬编码 `check` 目标，而 CMake/CTest 只提供 `test` 目标（driver 级 artifact，非上游测试失败） | 按 driver checkpoint 口径“记录并继续”；**权威测试账本以 conan 配方 build() 内 ctest 为准**，test-report.md 按真实账本重写 |
| 4 | 生成的 conanfile 缺上游测试执行、且硬编码设备路径 `CMAKE_INSTALL_PREFIX` | `conan-init` 通用模板未集成 ctest、误把 DEFAULT_PREFIX 写进 tc.variables | 移植 1.2.9 配方（build() 内签名 `cwalktest` 后跑 `ctest --output-on-failure`），不设安装前缀 |

## 源码修改

无补丁（`patches/` 为空）。

## 依赖版本

- 构建期：无外部 conan 依赖（零依赖纯 C 库）
- 工具链：clang 15.0.4 / cmake 4.1.2 / llvm-objcopy / binary-sign-tool（跑上游测试前签名 `cwalktest`，OHOS 未签名 ELF 不可执行）

## 测试口径（五维账本）

- `N_static`（上游静态声明）= 180：`CMakeLists.txt` 中 `create_test(DEFAULT ...)` 行数（14 个 unit：absolute/basename/dirname/extension/guess/intersection/is_absolute/is_relative/join/normalize/relative/root/segment/windows）
- `N_registered`（CTest 注册）= 180：`create_test()` 内部逐条 `add_test(NAME unit_test ...)`
- `N_executed`（实际执行）= 180，pass 180 / fail 0 / skip 0（`100% tests passed, 0 tests failed out of 180`，conan-create.log）
- 未执行分类数 = 0
- `N_consumer`（消费者测试）= 1 程序 / 8 断言，全过（`cwalk consumer test passed: 8 assertions`）
- 适配后合计 = 181（上游 180 + 消费者 1），通过率 181/181

## 验证结果

```bash
conan-verify G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS（报告 23 项 ✅）
ctest: 100% tests passed, 0 tests failed out of 180
consumer: cwalk consumer test passed: 8 assertions
产物: libcwalk.a 20944 bytes（build 树与 package 树两处一致）
```

## 首包跨机验证（手册/10 §7）

本任务为 B 机首包验证载体（A 机 worktree `A-cwalk-1.2.8` 跑同包同版本做四项对比：
测试账本 / 产物清单 / conan-verify 结论 / 环境指纹；**不比二进制 sha**）。

**编译结束** 2026-09-23 23:59（conan-verify PASS）
**最终状态**: built
---

**编译结束**: 2026-09-24 00:10
**最终状态**: built
