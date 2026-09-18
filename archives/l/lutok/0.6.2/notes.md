# lutok 0.6.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-17
- 编译器: clang/clang++ 15.0.4（OHOS SDK，libc++）
- 设备: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）
- 状态: built

## 编译步骤

1. 源码采用官方 release 附件（`make dist` 产物，自带 `configure` / `Makefile.in` /
   `admin/` 辅助脚本），无需 autoreconf：
   `https://github.com/jmmv/lutok/releases/download/lutok-0.6.2/lutok-0.6.2.tar.gz`
   （设备重算 SHA256 `1ef51f3741d28e27b09dfaee61ab432966cff56f50940eca1cbacffc11baa2ad`）
2. 配方 `generate()`：
   - `PkgConfigDeps` 生成 `lua-5.4.pc`（lua/5.4.8 的 `pkg_config_name=lua-5.4`），
     `m4/lua.m4` 第一级探测即命中；
   - 自写 `atf-c++.pc` / `atf-sh.pc`（指向 atf 包实际路径 + `.a` 拷贝目录），
     注入 `PKG_CONFIG_PATH`；
   - 生成 `lua.hpp` 包装头（私有 build prefix）与 `mktemp` shim（PATH 前置）；
   - `AutotoolsToolchain(prefix=<package_folder>)`，configure 参数：
     `--build/--host=aarch64-unknown-linux-gnu --enable-atf --with-doxygen=no`。
3. `configure && make -j1`：构建 `liblutok.so.3.0.0` + 6 个 atf-c++ 测试程序 + `examples_test`。
4. 上游测试（无 kyua）：`-l` 枚举用例 + `prog <case>` 逐用例执行（97 用例）→ `make install`
   → `examples_test`（atf-sh，4 用例，真实编译并运行 4 个上游示例）。
5. `build()` 内依次执行：`make` → 97 个 atf-c++ 用例逐用例执行 → `make install`
   （`--prefix` 即包目录，examples_test 依赖该安装）→ atf-sh `examples_test`；
   `package()` 负责删除 `.la` 并随包安装 `lua.hpp`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one`（config.guess 2018-08-29 不认识 HarmonyOS，uname -s=HarmonyOS） | 平台字符串不在 config.guess 的匹配表内 | 显式传 `--build/--host=aarch64-unknown-linux-gnu`（不修改上游文件） |
| 2 | `config.status: error: could not setup config files machinery`（写 `./confXXXXXX/subs1.awk` Permission denied） | HMDFS 上 toybox `mktemp -d` 在 `umask 077` 下建出的目录（drwx--S---）不可写 | 配方生成 mkdir 版 `mktemp` shim 并前置 PATH（与 skypat 3.2.0 同源处置，本轮在 lutok 上实测复现并验证） |
| 3 | 链接测试程序报 `libtool: error: cannot find the library '//lib/libatf-c.la'` | atf/0.23 制品包以 `prefix=/` 构建：`.pc` 为 `includedir=//include`，`.la` 的 `dependency_libs` 指向 `//lib/libatf-c.la` | 自写 atf `.pc`，并把 `libatf-c++.a`/`libatf-c.a` 拷贝到构建目录私有 link 目录供 `-L` 使用，绕开坏 `.la`（不改动依赖包） |
| 4 | `Failed to execute /data/service/hnp/bin/bash: No such file or directory`（examples_test 无法启动） | atf-sh 编译期默认 `ATF_SHELL=/data/service/hnp/bin/bash`（CI worker 路径），设备上不存在 | 运行 examples_test 前显式设置 `ATF_SHELL`（及 `ATF_LIBEXECDIR`/`ATF_PKGDATADIR`）指向设备真实路径 |
| 5 | `#include <lua.hpp>` 找不到 | lua/5.4.8 与 5.4.8.1 制品均只安装 `*.h`，缺上游发行版自带的 C++ 包装头 `lua.hpp`；lutok 的公开头 `c_gate.hpp` 与多个源文件依赖它 | 配方在私有 build prefix 生成标准四行包装头供构建使用，并将其安装到包内 `include/`，保证消费者包含 `<lutok/c_gate.hpp>` 时可用（lua-rapidjson 0.6.0 同族先例） |
| 6 | profile `compiler.cppstd=17` 与上游强制的 C++20 冲突 | `AX_CXX_COMPILE_STDCXX(20,...)` 把 `-std=c++20` 追加到 `CXX`，而 conan 的 `CXXFLAGS` 中 `-std=c++17` 位置更靠后（后出现者生效） | `tc.extra_cxxflags.append("-std=c++20")` 置于标志列表尾段，保证最终生效标准为 C++20 |

## 源码修改

无。上游源码保持原样，无补丁（补丁项为空）；全部平台差异通过配方级处置完成。

## 依赖版本

- lua/5.4.8（静态库，`pkg_config_name=lua-5.4`；其 `.pc` 由 PkgConfigDeps 生成）
- atf/0.23（`test_requires`，静态库；`.pc`/`.la` 已被证明不可迁移，另行封装）
- 编译器：clang/clang++ 15.0.4（OHOS SDK），libc++
- Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64`（设备 profile `ohos-aarch64-device`）

## 验证结果

```bash
# 上游 6 个 atf-c++ 程序（-l 枚举 + 逐用例执行）：
SUMMARY total=97 passed=97 failed=0
SUITE c_gate_test cases=2 / debug_test cases=2 / exceptions_test cases=4 /
operations_test cases=19 / stack_cleaner_test cases=4 / state_test cases=66

# examples_test（atf-sh，真实编译并运行 4 个上游示例）：
SUMMARY total=4 passed=4 failed=0
SUITE examples_test cases=4

# 说明：ATF 程序在 kyua 之外裸执行会打印
# "WARNING: Running test cases outside of kyua(1) is unsupported"，
# 属预期（无隔离/超时控制），退出码语义不变（0=通过）。

# 消费者测试（conan create 的 test_package，CMakeDeps + CMakeToolchain）：
# test_lutok 6 处断言全部通过（do_string 求值、native 模块调用、
# stack_cleaner、失败脚本异常、c_gate 裸 lua_State 访问）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| liblutok.so.3.0.0 | 359 KB | 共享库（SONAME liblutok.so.3），本包实际交付 |
| liblutok.a（未交付） | — | 本包以 `--enable-shared --disable-static` 构建；配方 `shared=False` 时可选构建 |
| include/lutok/*.hpp | — | 公开头（含 c_gate/state/operations/exceptions/stack_cleaner/debug/test_utils） |
| include/lua.hpp | — | 依赖包缺失的 Lua C++ 包装头（配方生成，四行标准内容） |
| lib/pkgconfig/lutok.pc | — | pkg-config 元数据 |
| tests/lutok/* | — | 上游测试程序 + Kyuafile + examples_test（上游安装布局） |

## 注意事项

1. `--enable-atf` 会安装测试程序到 `<prefix>/tests/lutok`（上游行为，保留）；
   测试程序静态链入 atf，不构成运行期依赖。
2. `examples_test` 依赖已安装的 lutok.pc 与示例目录，因此必须在 `make install`
   之后运行（配方已按此顺序处理）。
3. atf 的 `.pc`/`.la`/编译期 `ATF_SHELL` 在任何消费方都不可直接使用；本配方
   在生成阶段一并修正，若后续 atf 包修复迁移性问题，可回收相关处置。
4. lua.hpp 属依赖包缺口：若后续 lua 制品提供该头，配方中生成的同名头可移除，
   当前两者内容一致，不产生冲突。
5. 知识库 E490（autotools helper 脚本执行位）未命中：源为官方 release tar.gz，
   `configure`/`config.status` 实测直接执行成功（见 `reports/conan-create.log`），
   无需 chmod 修复。

## 归档状态

- 归档状态: built（与 manifest.yaml 一致）
---

**编译结束**: 2026-09-17 16:22
**最终状态**: built
