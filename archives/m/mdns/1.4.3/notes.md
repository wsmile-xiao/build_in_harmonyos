# mdns 1.4.3 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt`；**配方按 header-only 打包，不调用上游 CMake**）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos`，OHOS SDK）
- 状态: built

## 软件形态

`mjansson/mdns` 是**单头文件** mDNS/DNS-SD 库（C，公开域 / Unlicense）：

| 文件 | 作用 |
|---|---|
| `mdns.h`（1618 行） | 库本体，全部 `static inline` 实现，消费者 `#include "mdns.h"` 即可 |
| `mdns.c`（1264 行） | 上游**演示程序**（`main()`：`--discovery/--query/--service/--dump`） |
| `CMakeLists.txt` | `add_library(mdns INTERFACE)` + 可选 example（`MDNS_BUILD_EXAMPLE`，默认 ON）+ install（只装 `mdns.h` 与 CMake 包配置） |

- **零第三方依赖**：`mdns.h` 只 `#include` libc 头（`stdint/stddef/stdlib/string/fcntl/unistd/sys/socket/netinet/in`）；`grep -c pthread mdns.{c,h}` = 0，OHOS 不注入任何 `system_lib`。
- **上游无 `tests/` 目录**，CMakeLists 0 处 `enable_testing()`/`add_test()` ⇒ 上游测试总数 **N=0**（四口径清点与取数命令见 `reports/test-report.md`）。
- 1.4.3 版本对应 tag `1.4.3`（`git ls-remote --tags` → `1727be060294…`），sha256 三路一致 `be1fd8e35599cb7d…d480483`。

## 编译步骤

配方是 header-only（无 build 阶段），真实验证分两条线：

```bash
# ① Conan 配方验证（CI 同链路）
conan create archives/m/mdns/1.4.3 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
#   source() 下载并校验 sha256 → package() 装 mdns.h + LICENSE
#   → test_package 编译消费者 test.c 并直跑：1..44 / 44 checks, 0 failures

# ② 原生上游构建 + 演示程序端到端（设备实测，沙箱 HOME）
cmake -S src -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build -j2          # [100%] Built target mdns_example
./build/bin/mdns_example         # 真实组播发现 14 条应答，rc=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备 CMake 4.1.2 拒绝上游 `cmake_minimum_required(VERSION 3.0)`（`Compatibility with CMake < 3.5 has been removed`） | CMake ≥4.0 移除 <3.5 兼容 | 原生构建加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`；**配方不受影响**（header-only 不调上游 CMake）。知识图谱已有 `DRAFT-E321-cmake4-policy-version-minimum`，按 §3.8 不新建草稿 |
| 2 | `init-build` 报 `conandata.yml/conanfile.py/test_package 模板不可用` | `init_archive` 按无 `.tmpl` 后缀名查模板，仓库实物是 `*.tmpl`（backlog #69 同族现场实证） | 先补 `manifest.yaml` 再走官方 `conan-init`（按 `.tmpl` 查找，四件套生成成功），随后按 header-only 形态改写 `conanfile.py` 与 `test_package/` |
| 3 | `init-build` 生成的 `manifest.yaml` 残留占位符（`{software}`、`{BUILD_SYSTEM}`）且 `build.system` 落成 `autotools` | 模板占位符与 `init_archive._manifest_template()` 的替换键不一致 | 手工补齐 `manifest.yaml`（software/status/build_system=cmake/source.sha256），`conan-init` 才能正确判构建系统 |
| 4 | 演示程序 `mdns.c` 用 `-std=c99` 编译报 `strncasecmp` 未声明 + `struct ip_mreq` 不完整 | `mdns.h` 依赖 POSIX/GNU 特性宏（`-std=c99` 关掉默认 `_DEFAULT_SOURCE`） | 用 clang 默认 `gnu17`（CMake 不设 C 标准即默认）零警告通过；`test_package/CMakeLists.txt` 不设 `C_STANDARD` |

## 源码修改

无（`patches: {}`——上游源码零改动，W0 的 ISA/glibc printf grep 均 0 命中，无需任何 portability 补丁）。

## 依赖版本

- 运行期/编译期第三方依赖：**零**（Conan `requires` 为空，`PF4 依赖闸` 无对象）。
- 工具链：clang 15.0.4（OHOS SDK）、CMake 4.1.2、Ninja/Make 4.4.1、conan 2.29.1。

## 验证结果

```bash
# 采信轮（干净缓存）conan create + conan-verify → 见 reports/conan-verify-report.md
# 消费者断言：1..44 / # mdns consumer test: 44 checks, 0 failures   （44/44）
# 原生构建：cmake --build → [100%] Built target mdns_example        （rc=0）
# 演示程序：./mdns_example → 14 条真实 mDNS 应答 + Closed sockets    （rc=0）
# 上游测试：N=0（四口径清点），N′=0，TOTAL=PASS+FAIL+SKIP+NOT_RUN=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | header-only 配方（`package_type = "header-library"`，`package_id` 清空） |
| `conandata.yml` | 官方源 `https://github.com/mjansson/mdns/archive/refs/tags/1.4.3.tar.gz`，sha256 `be1fd8e3…`（三路一致） |
| `manifest.yaml` | ARCHIVE-SPEC v2.0 版本级清单，`status: built` |
| `test_package/` | 消费者测试 `test.c`（44 断言）+ `CMakeLists.txt` + `conanfile.py`（`self.run` 直跑）+ `MANIFEST.yml` |
| `reports/` | `test-report.md`、`native-build-and-example-run.md`、`conan-verify*.md`（工作区证据，不进 PR） |

## 注意事项

- 交付形态是**头文件包**（无 `.a`/`.so`，与上游 INTERFACE 库一致）；消费者用 `find_package(mdns)` + `mdns::mdns`。
- 上游 0 个可运行测试入口是**清点结论**，不是「测试通过」也不是「跳过」；适配后 44 条断言全部是鸿蒙侧新增验证，不进上游分母。
- CCI（Conan Center）同名配方同样按 `header-library` 打包；CCI 对 Linux/FreeBSD 追加的 `system_libs = ["pthread"]` 在本包无调用面（`grep pthread` 0 命中），未搬运。
