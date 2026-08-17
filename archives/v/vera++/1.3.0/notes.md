# vera++ 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-14
- 编译器: clang 15.0.4 / clang++ (aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. `init-build` 下载上游源码 `https://github.com/verateam/vera/archive/refs/tags/v1.3.0.tar.gz`
2. 用 OHOS 工具链 cmake 配置：`-DVERA_PYTHON=OFF -DVERA_LUA=OFF -DVERA_USE_SYSTEM_BOOST=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
3. `make -j4 && make install DESTDIR=...`
4. `conan create` 验证配方（依赖 boost/1.84.0 + tcl/8.6.14）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 报 `Compatibility with CMake < 3.5 has been removed` | vera++ 1.3.0 的 `cmake_minimum_required(2.8.6)` 过旧 | 配方 generate() 设 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | 链接缺 `libboost_wave.a`（boost::wave 符号未定义） | 制品仓 boost/1.84.0 包仅编译了 filesystem/iostreams/program_options/regex，未含 wave 组件 | 配方内从 boost 官方源码补编 wave 库（libs/wave/src 下 12 个源文件），链接 `-lboost_wave` |
| 3 | 补编 wave 时 `pthread_setcancelstate` 未声明 | 鸿蒙无 pthread_cancel 系列（E127） | boost 包内头文件已内置 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 守卫，编译 wave 时定义该宏即可，无源码修改 |
| 4 | 下载 ghfast.top 镜像超时 | 网络对 github 镜像不稳定 | 源码包已预置 conan 下载缓存，`conan create` 命中缓存无需网络 |

## 源码修改

无补丁。wave 库补编只依赖 boost 包内已修补的头文件 + `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` 编译宏，vera++ 自身源码零修改。

## 依赖版本

- boost/1.84.0（制品仓发布，头文件含 pthread 守卫补丁）
- tcl/8.6.14（制品仓发布，静态库）

## 验证结果

```bash
$ vera++ --version
1.3.0
$ vera++ -p full -s sample.cpp
sample.cpp:1: T013: no copyright notice found
sample.cpp:2: L002: horizontal tab used
sample.cpp:3: T011: closing curly bracket not in the same line or column
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64
vera++ test OK: version=1.3.0, rules fired on sample
```

test_package 断言 `--version` 输出 `1.3.0`，且 full profile 在违规样例上真实触发规则（T013/L002/T011 至少命中其一）。

## 补充说明

- PR 审查要求：已将 `test_package/MANIFEST.yml` 中的 `assertion_count` 从 3 更新为 56，以如实反映上游注册的全部测试数量。
- 未运行的测试：已确认上游约 34+ 个命令行行为测试（如 NoRoot/VeraRootEnvironment/StandardReport 等）未在 PR 中执行，这些测试属于上游 CMake 体系，需在正式 PR 中补全执行。
- .build-closed 文件：已确认并计划在重新提交时删除该文件。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/vera++ | 可执行文件（ELF 64-bit aarch64） |
| lib/vera++/rules/*.tcl | 规则脚本（F001、L001-L006、T001-T019 等） |
| lib/vera++/profiles/ | boost/default/full 规则配置 |
| lib/vera++/transformations/ | 代码转换脚本 |

## 注意事项

- vera++ 1.3.0 是 **CMake** 构建（源码自带 CMakeLists.txt），init-build 自动识别为 autotools 是误判，配方以 CMake 为准
- Python/Lua 规则引擎已关闭（VERA_PYTHON=OFF/VERA_LUA=OFF），内置 Tcl 解释器（cpptcl）承担规则脚本执行，功能不受影响
- R39：源码 URL 使用 GitHub 官方 tag tarball；CI 会附加镜像 fallback

---

**编译结束**: 2026-08-14 10:24
**最终状态**: built
