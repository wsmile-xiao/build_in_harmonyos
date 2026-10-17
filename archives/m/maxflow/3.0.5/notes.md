# maxflow 3.0.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27（真机 shadow CI r6 通过；设备 clang 15.0.4 / CMake 4.1.2 / ohos-aarch64 profile）
- 编译器: clang/clang++（/data/service/hnp/bin）
- 状态: built（L0/L1/L4/L5 pass，L2 skip 无 bin/，上游测试 10/10，test_package 7/7）

## 上游与依赖审计（W0/W1）

- 上游仓库: https://github.com/gerddie/maxflow ，tag `3.0.5`（commit 42401fa，
  2015-11-22；无 `v` 前缀）。Debian/Ubuntu/Mageia/Guix/MSYS2 均以该仓库打包
  （libmaxflow-dev 3.0.5）。
- 许可证: GPL-3.0-or-later（GPL.TXT + 文件头 GPLv3+ 声明）。
- 语言/构成: 纯 C++（graph.cpp/graph.h/block.h/maxflow.cpp/maxflow.h +
  test_maxflow.cpp），约 3.4k 行。
- 依赖数量: 0（运行时/构建/测试均无外部依赖，只需 CMake ≥3.5 与 C++ 工具链）。
- 缺失依赖: 无。不需要拆分依赖适配。

## 构建系统分析

- 顶层 CMakeLists：`ADD_LIBRARY(maxflow SHARED maxflow.cpp)`（硬编码 SHARED，
  无选项）；`ADD_SUBDIRECTORY(maxflow)` 安装 block.h/graph.h/graph.cpp；
  顶层安装 maxflow.h 与 pkg-config 文件；无条件 `ENABLE_TESTING()` +
  `ADD_TEST(maxflow test-maxflow)`。
- 头文件布局：`include/maxflow-3.0/`（`VERSION = MAJOR.MINOR = "3.0"`）+
  `include/maxflow-3.0/maxflow/`；`maxflow.h` 内部 `#include <maxflow/block.h>`
  等，因此消费者 include 目录是 `include/maxflow-3.0`。`graph.cpp` 作为
  "头文件" 安装是上游有意为之：`maxflow.h` 在
  `MAXFLOW_INCLUDE_TEMPLATE_IMPLEMENTATION` 下会包含它（仅编译库时定义，
  消费者不定义，不会把模板实现拉进自己的 TU）。
- 已知上游怪癖（不修）：3.0.5 tag 里 `MICRO_VERSION 4` 未随 tag 更新，
  `maxflow.pc` 的 Version 字段为 3.0.4；SOVERSION 推导为 libmaxflow.so.0。
  Debian 打包保留同样行为，消费者经 Conan cpp_info 使用不受影响。
- 无 CMake package config（`EXPORT MaxFlow` 悬空），消费者使用本包
  CMakeDeps 生成的 `find_package(maxflow)` + `maxflow::maxflow`。

## 测试审计

- 上游唯一测试：`test_maxflow.cpp`（3 个测试函数 test_1/test_2/test_3，
  共 10 个断言：3 个 maxflow() 流量值 + 7 个 what_segment 归属检查），
  以单个 ctest 项 `maxflow` 注册；任一断言失败进程返回 EXIT_FAILURE，
  stderr 汇总行为 `N of 3 test failed`。
- 无外部服务/网络/POSIX 特殊行为依赖，可整体在 HarmonyOS PC 执行。
- 配方在 `build()` 内通过 `ctest -N` + `ctest --output-on-failure` 执行，
  结果解析自 `Testing/Temporary/LastTest.log`，以
  `HMBS_UPSTREAM_TEST_RESULT` 标记输出（同 leatherman 惯例）；非零退出
  或断言失败会让 Conan 以非零码结束。
- test-maxflow 链接构建树内 libmaxflow.so，鸿蒙无可用 RPATH，运行前把
  构建目录追加进 `LD_LIBRARY_PATH`（同 mcfp 配方技法）。

## 编译步骤

本机未执行（无 Conan/OHOS 交叉工具链）。预期真机命令由隔离 job runner 执行：

```sh
conan create archives/m/maxflow/3.0.5 --profile=<ohos-profile> --build=missing
```

test_package 随 `conan create` 自动构建运行；配方内 `can_run(self)` 保证
仅在可执行环境下跑上游 ctest。

## 源码修改

| 文件 | 补丁 | 内容 |
|------|------|------|
| CMakeLists.txt | patches/0001-bump-cmake-minimum-version-to-3.5.patch | `CMAKE_MINIMUM_REQUIRED(VERSION 2.8.5 FATAL_ERROR)` → `3.5 FATAL_ERROR`。原因：CMake 4.x 移除 <3.5 兼容模式直接报错（知识库错误模式 E103 bump-cmake-minimum-version）。项目设置的 CMP0003/CMP0012/CMP0042 策略在 3.5 下均有效 |
| CMakeLists.txt | patches/0002-drop-versioned-so-symlinks-hmdfs.patch | 注释掉 `SET_TARGET_PROPERTIES(maxflow PROPERTIES SOVERSION/VERSION ...)`。原因：HMDFS（/storage）无 symlink(2)，CMake 建 libmaxflow.so.0/.so 软链时报 `cmake_symlink_library: Permission denied`（真机 r4 实测；知识库 DRAFT-libfreenect-0.5.3-hmdfs-shared-lib-versioned-symlink 同型）。去版本化产扁平 libmaxflow.so，消费者链接方式不变 |

## 真机 shadow CI 迭代记录

| 轮次 | 现象 | 根因 | 解法 |
|------|------|------|------|
| r1 | `Package type is 'library', but no 'shared' option declared` | Conan 2 对泛型 library 类型强制要求 shared 选项；上游硬编码 SHARED 无选项 | package_type 改 `shared-library`（仓库 161 个配方同款惯例） |
| r2/r3 | `cmake: inaccessible or not found`（Error 127） | 隔离 job 非交互 runner 环境 PATH 无 hnp 工具目录，裸 cmake/ctest 解析不到 | generate() 里用 build-env 脚本（Environment.vars(scope="build").save_script）把 `/data/service/hnp/cmake.org/cmake_4.1.2/bin` 与 `/data/service/hnp/bin` 注入 PATH（nymphcast「PATH 探测 + hnp 兜底」同型；conf_info.define 对本节点不生效，r3 已验证） |
| r4 | `cmake_symlink_library: Permission denied`（编译/链接已过） | HMDFS 无 symlink(2)，CMake VERSION/SOVERSION 需建版本软链 | 补丁 0002 去版本化，产扁平 libmaxflow.so |
| r5 | 包本体全绿后，test_package 的 cmake 又报 not found | PATH 注入只在主配方生效，消费者配方是独立上下文 | test_package/conanfile.py 的 generate() 加同样注入 |
| r6 | ✅ 全部通过（exit 0） | — | L0/L1/L4/L5 pass、L2 skip(无 bin/)、L1e 负向确认、上游 10/10、test_package 7/7 |

## 验证结果（真机 shadow CI 终态，2026-09-27 r6）

```text
exit code = 0（排队等待 0 秒）
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
  L1a/L1b/L1c ok；L1e 破坏性反向验证确认（lib/、include/ 被破坏后 test 失败）
L2_RESULT=skip: no bin/ dir（纯库正常）
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"ctest",
  "discovered":3,"executed":10,"passed":10,"failed":0,"skipped":0}
test_package: "test_maxflow: all assertions passed"（7/7）
```

本机前置（W4）时的交叉冒烟与 SHA256/补丁 dry-run 记录见 git 历史 r0 前置提交。

## 依赖版本

无外部依赖。

## 验证结果（W4 本机前置）

```bash
# 源码归档 SHA256 复核（本机执行 PASS）
sha256sum maxflow-3.0.5.tar.gz
# e73a7be173fb95e93366c8128f9f478bc2fe406f7f83eb998fc34e18eaabb612

# conanfile.py / test_package py 语法检查（本机执行 PASS，python 3.12）
python -m py_compile conanfile.py test_package/conanfile.py

# conandata.yml / manifest YAML 结构检查（本机执行 PASS）
python -c "import yaml,sys; yaml.safe_load(open('conandata.yml',encoding='utf-8')); yaml.safe_load(open('manifest.yaml',encoding='utf-8'))"

# 补丁可应用性（对本机解包的 3.0.5 tag 源码 --dry-run PASS）
patch -p1 --dry-run < patches/0001-bump-cmake-minimum-version-to-3.5.patch

# test_package 消费者源码本机冒烟（g++ 编译 + 直连本机源码头文件，PASS 7/7）
```

CI 门禁自检（对照 ci/conan/build_and_test.sh）：L0a-L0e 文件齐全；
L0f conandata patches 为 list 格式；L0d test() 含字面 `self.run()`；
L0h/L0g 无 shell 环境变量依赖、无硬编码 remote。

## 注意事项 / 下一步（真机 shadow CI，单包排队）

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job maxflow-3.0.5 \
  --package archives/m/maxflow/3.0.5 \
  --repo-source <设备上已有仓库路径>
sh "$HOME/ohos-users/codex/maxflow-3.0.5/run-conan-heavy.sh"
# 关注: L0-L5 结果、HMBS_UPSTREAM_TEST_RESULT(期望 executed=3 passed=3)、
#       test_package ./test_maxflow (7/7 断言)
```

- 真机通过后：manifest 状态 `prepared` → `built`，MANIFEST.yml 回填
  run_status，PR 描述补《验证结果》。
- 若制品仓 `maxflow/3.0.5` 已被占用，按 R37 递增为 `3.0.5.1` 并同步目录/
  配方/test_package/manifest/notes/分支名。
