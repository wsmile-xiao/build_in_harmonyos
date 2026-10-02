# uhdm 1.86 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 依赖（conan 制品仓现成 ohos-aarch64 二进制，无需源码编译）
conan install --requires=capnproto/1.3.0 --requires=googletest/1.12.1 -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -g CMakeDeps -g CMakeToolchain -of=<deps>

# 2. pip 代码生成依赖（构建机 python3.12，社区源 pypi.cnb.cool）
pip3 install orderedmultidict==1.0.2   # 连带 six==1.17.0

# 3. configure（host 分支：跳过 third_party/capnproto 与 third_party/googletest 子模块）
cmake -S <src> -B <build> \
  -DCMAKE_TOOLCHAIN_FILE=<deps>/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DUHDM_USE_HOST_CAPNP=ON -DUHDM_USE_HOST_GTEST=ON -DUHDM_BUILD_TESTS=ON \
  -DCAPNP_EXECUTABLE=<capnproto 包>/bin/capnp \
  -DCAPNPC_CXX_EXECUTABLE=<capnproto 包>/bin/capnpc-c++

# 4. 构建 + 测试（TMPDIR 必须指向可写目录，E544-E3AD 口径）
cmake --build <build> -j8
cd <build> && TMPDIR=$HOME/tmp ctest --output-on-failure
```

要点：UHDM_USE_HOST_CAPNP=ON 时 CMakeLists 仅 `find_package(CapnProto)` 不设 `CAPNP_EXECUTABLE`，该变量须由消费方显式提供（配方 generate() 注入）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首轮 ctest -j4 并发 7/43 瞬时失败（0.01-0.02s 即崩，含 vpi_get_test/classes_test 等） | 共享 TMPDIR 下并发竞态的瞬态环境问题（非产品缺陷）：串行重跑 43/43 全绿、单独直跑各"失败"二进制亦全绿 | 串行运行 ctest 复测通过；PR 台账双口径留证 |
| 2 | /tmp 只读（E002/E544-E3AD 口径） | OHOS 平台 /tmp 只读，测试二进制创建临时文件 abort | TMPDIR 指向 $HOME/tmp（可写） |
| 3 | UHDM_USE_HOST_CAPNP=ON 时 CAPNP_EXECUTABLE 未定义 | 上游 CMakeLists host 分支不设置该变量（子模块分支才 FORCE 设置） | configure 显式传 -DCAPNP_EXECUTABLE/-DCAPNPC_CXX_EXECUTABLE；配方 generate() 同样注入 |
| 4 | G2：uhdm-dump 运行时 `Error relocating ... _ZTVN4UHDM18ElaboratorListenerE: symbol not found` | libuhdm.so 无 SONAME：CMake 不认识 HarmonyOS（E092），CMAKE_SONAME cache 变量（UNINITIALIZED+FORCE）进 CMakeCache.txt 但不进 link.txt；DT_NEEDED 内嵌相对路径 lib/libuhdm.so，loader 按 CWD 相对解析失败，库未加载 → 符号查找失败是下游症状（nm -D 实证 vtable 在 .so 内） | 配方默认静态（上游默认，消除运行时动态解析）；shared=True 时 CMAKE_SHARED_LINKER_FLAGS 显式 -Wl,-soname,libuhdm.so（OHOS clang15/lld 驱动实测遵循） |
| 5 | G2（切静态后）：test_uhdm 链接期 undefined capnp::*/kj 符号 | 静态 libuhdm.a 把符号解析推迟到消费者；capnproto 原仅 tool_requires 声明（shared 时 capnp 对象已嵌入 libuhdm.so 掩盖问题） | 双声明：tool_requires（capnpc 代码生成）+ requires（链接期/公共头），package_info requires=capnproto::capnp（kj 经组件边带入） |
| 6 | W3 本地 CI：JC6 误判"PR 涉及 62 个软件包"；对齐 base 后 JC1/JC5 又扫出上游存量隐藏文件 | JC incremental 模式 = git diff origin/main...HEAD：origin（fork）main 跟踪 ref 陈旧 → diff 卷入 fork 点后上游合入的 62 包；对齐后 diff 为空 → 脚本回退 full 模式（整仓扫描）命中上游自己提交的存量文件 | 本地 origin/main 跟踪 ref 对齐 PR 真实 base（git fetch upstream main:refs/remotes/origin/main）+ finish 前预提交干净 15 文件集（.gitignore 天然排除状态文件）→ W3 重跑 1/1 全绿 |

## 源码修改

无（上游 v1.86 源码未做任何修改，patches/ 为空）。

## 依赖版本

- capnproto/1.3.0（conan 制品仓 ohos-aarch64 现成二进制，package_id 23898865f2867d65；tool_requires 提供 capnp/capnpc-c++ 代码生成器）
- googletest/1.12.1（conan 制品仓 ohos-aarch64 现成二进制；target GTest::gtest/gmock/gtest_main）
- Python 3.12.9 + orderedmultidict==1.0.2 + six==1.17.0（构建机 pip 依赖，仅 generate.py 代码生成期使用，不进制品）

## 验证结果

上游测试台账（R51 三步法）：
- 清点：tests/*.cpp 共 17 个测试源（CMakeLists `register_tests()` 显式枚举，另有 test_util.h）→ 17 个测试二进制；ctest 注册 43 个 gtest 用例
- 实测（OHOS aarch64 本机，TMPDIR=$HOME/tmp）：
  - 首轮 -j4 并发：36/43（7 条瞬时失败 0.01-0.02s，共享 TMPDIR 并发竞态，见问题 #1）
  - 串行复跑：**43/43 PASSED（100%，exit 0）**，Total Test time ≈ 106s
  - 单独直跑失败样本 vpi_get_test：4/4 PASSED
- 上游 x86 基线对比：本环境为 OHOS aarch64 目标机原生执行，注册用例数与上游一致（43），无 skip/xfail

```bash
cd <build> && TMPDIR=$HOME/tmp ctest --output-on-failure
# => 100% tests passed, 0 tests failed out of 43
```

## 交付物

| 产物 | 说明 |
|------|------|
| libuhdm.a | C++17 VPI 数据模型库（静态，含生成的 model 对象；消费者须链 capnproto，见 package_info requires） |
| bin/uhdm-cmp / uhdm-dump / uhdm-hier / uhdm-lint | CLI 工具集（R38 声明于软件级 archives/u/uhdm/commands.json） |
| include/uhdm/*.h | 公共头（含生成的 uhdm_capnp_*.h） |
| share/uhdm/UHDM.capnp + cmake/uhdm_build_modules.cmake | schema 文件与 -include config.h 构建模块（cmake_build_modules） |

## 注意事项

- **SONAME 平台陷阱（E092 关联，新发现）**：CMake 无 HarmonyOS platform module，CMAKE_SONAME cache 变量不生效 → shared 库无 SONAME → DT_NEEDED 内嵌相对路径 → 运行时 relocation 失败；诊断时勿被 "symbol not found" 误导（符号在 .so 内，真因是库未加载）。
- **capnproto 双声明不可省**：tool_requires 与 requires 各司其职（代码生成 vs 链接期/公共头）；shared 构建会掩盖缺 requires 的链接问题，切静态才暴露。
- **W3/JC 空 diff 陷阱**：本地 fork main 跟踪 ref 陈旧 → JC6 误报多包；对齐后 diff 空 → JC 回退 full 模式扫出上游存量。对策：finish 前预提交干净文件集（状态文件 .gitignore 排除）。
- **test_package/build/ 是 in-tree 构建残留**（G2/W3 每次重生成）：.gitignore（build/、*.o）天然排除；手动暂存时勿整目录 add test_package/。

## 语言预检（R47）误报裁定

- lang-preflight 判定 python（detected_language=python）与任务 cpp 不匹配，工具自动写入 env_unsupported 终态
- 误报根因（scripts/ohc/lang_detect.py，代码级定位）：
  1. `_manifest_scan` 对 setup.py 使用递归 names（任意深度）匹配，`python/setup.py`（UHDM VPI SWIG 绑定包装脚本，仅打包 `_py_uhdm.so`）被误判为项目主 manifest；同函数中 CMakeLists.txt/meson.build/package.json 的检查均使用 tops（仅顶层），口径不一致
  2. 绑定救援规则（附录 D.4-2）要求 cpp 占比 ≥70%，实测 41/67=61% 未触发；冲突规则（→mixed）同阈值亦未触发
- 裁定证据：根目录 CMakeLists.txt 为主构建系统（CMAKE_CXX_STANDARD 17、CXX_STANDARD_REQUIRED ON）；`find_package(Python3)` 仅用于调用 generate.py 做代码生成；产物为 C++ 库（libuhdm）+ CLI 工具（uhdm-cmp/dump/hier/lint）；按附录 D.4-2（pybind11 类绑定包判 cpp）与 D.4-3（辅助脚本不算主体）应判 cpp
- 处置：按 cpp 继续适配；任务真终态时以 result 命令 `--force` 覆盖此误判终态；工具缺陷记入 SKILL_FEEDBACK
---

**编译结束**: 2026-09-30 00:38
**最终状态**: built
