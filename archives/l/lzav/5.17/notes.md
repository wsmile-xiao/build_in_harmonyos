# lzav 5.17 适配笔记

## 编译环境
- 构建系统: header-only（单头文件库，无构建系统）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-linux-ohos, OHOS 6.0)
- 状态: built
- 语言预检(R47): lang_detect 判 "other(none)" 属误判——lzav 为 C99/C++ 兼容 header-only
  库，官方 tag 仅 LICENSE/README.md/lzav.h 三个文件、无 .c/.cpp 实源可统计；
  按 R47 c↔cpp 兼容族不迁移，正常适配。

## 编译步骤
header-only 库无 configure/make：以 conan create + test_package 消费者编译/运行替代验证。
- conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
- 源码: https://codeload.github.com/avaneev/lzav/tar.gz/refs/tags/5.17
- sha256: b56a854a878fae9ca02793f9ac09a1b555d0801bde7897d8caace5cd88901b90

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan get() 报 BadZipFile | codeload URL 不以 .tar.gz 结尾，conan 无法识别格式 | conandata.yml sources 增加 filename: "lzav-5.17.tar.gz" |
| 2 | package() 后 "No files in this package!" | headeronly 模板 copy dst 用相对路径未落到 package 目录 | 改用 args-parser 同款：dst=self.package_folder + cpp_info.includedirs=["."] + package_type="header-library" + cmake_layout(src_folder=".") |
| 3 | conan create 报 "Package type is 'library', but no 'shared' option declared" | package_type=library 缺 shared option | 改用 header-library 类型（header-only 库正解） |
| 4 | 消费者测试 bound 断言误失败 | lzav_compress_bound 预留余量 > src_len+1024 | 断言放宽为 (src_len, src_len*2] 区间 |
| 5 | test_package 初始为 executable 错误模板（调用不存在的 lzav 二进制） | conan-init 默认模板 | 重写为 header-only 消费者 CMake 测试 |

## 源码修改
无补丁（patches/ 为空）。test_package/ 内新增消费者测试与鸿蒙专项测试源码：
- test.c — lzav_consumer_test（消费者验证）
- test_ohos.c — lzav_ohos_test（鸿蒙专项）

## 依赖版本
无外部依赖（W0 预检通过：preflight_check.sh 无依赖声明）。

## 验证结果（双口径台账）

### 上游测试全量枚举（官方 tag 5.17 源码，可复制枚举）
官方 tag tarball 清单（tar tzf，全部文件）：
```
lzav-5.17/LICENSE
lzav-5.17/README.md
lzav-5.17/lzav.h
```
枚举结论：无 tests/ 目录、无测试源文件、无 Makefile/CMakeLists/configure 构建目标、
无 ctest/GTest/Meson 注册项、无测试脚本、无样例/基准可执行入口（README 仅含静态基准数据表）。

| 口径 | 数量 |
|---|---|
| source_declared_total（官方 tag 源码测试声明总数） | 0 |
| configured_executable_total（当前 OHOS 配置实例化可执行用例数） | 0 |
| executed_passed_total | 0 |
| failed / uninstantiated / 硬阻塞 | 0 / 0 / 0 |

映射说明：声明数=0，无"声明→构建目标→注册→执行"链路可实例化，不存在互斥分支或
未实例化项。0/0 口径下不产生通过率分母，按规则如实填 0 并附枚举证据。

### 本轮新增实际执行用例（与上游分别计数，不重复充数）
| 用例 | 源文件 | 构建目标 | 执行日志 | 结果 |
|---|---|---|---|---|
| 消费者验证 | test_package/test.c | lzav_consumer_test | conan-create.log: RUN ./lzav_consumer_test → PASS | 1/1 |
| 鸿蒙专项 | test_package/test_ohos.c | lzav_ohos_test | conan-create.log: RUN ./lzav_ohos_test → PASS(4 checks) | 1/1 |

鸿蒙专项测试运行时证据（真实设备内核）：
```
uname sysname = HarmonyOS, release = HongMeng Kernel 1.12.0, machine = aarch64
PASS: lzav_compress_default compresses on HarmonyOS (comp_len=185)
PASS: round-trip equals source on HarmonyOS (1 MiB, dec_len=1048576)
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（header-library, cmake_layout, package 到 include） |
| conandata.yml | 官方 codeload URL + sha256 + filename |
| test_package/ | CMake 消费者测试 + 鸿蒙专项测试 + MANIFEST.yml |

## 注意事项
- lzav 为单头文件库（lzav.h 77KB），无 CLI 产物 → 无需 commands.json（R38 库类型豁免）
- 无系统同名库冲突（G3 通过）
---

**编译结束**: 2026-09-19 02:18
**最终状态**: built
