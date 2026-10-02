# DRAFT-libgpr-1.82.0-cmake-component-split-build-prerequisites

> 草稿知识项（draft）。**不预占正式 E 编号，禁止直接 promote**。
> 触发事件：`libgpr 1.82.0`（= grpc 1.82.0 的 `gpr` 组件拆分，task #8219，PR !13983）。
> 同族先例：`libgrpc_unsecure/1.82.0`、`libgrpc_authorization_provider/1.82.0`。

## 使用说明（何时用）

当你**不打算交付整个上游工程**，而是把上游单一 CMake 工程**拆成多个只交付单个 target 的 conan 组件包**（module split）时用本文。典型症状按出现顺序：

1. configure 走完、`-- Generating done` 后却报 `CMake Generate step failed`，逐条报
   `Error evaluating generator expression ... $<TARGET_FILE:xxx>` / `No target "xxx"` —— 你想关掉的插件/codegen target 其实是 generate 期的硬前提；
2. 打开 `INSTALL` 后 install 阶段报缺 target（上游 `install(TARGETS ...)` 覆盖全量 target）；
3. 打开 `BUILD_TESTS` 后 configure/generate 报 `file COPY cannot find ... third_party/<子模块>/...proto`（release tarball 不含 submodule）；
4. 最后发现 `requires` 里塞进了上游顶层 `find_package` 的全部包，而交付 target 一个符号都没用。

## 适用范围

满足**任一**条件的 CMake 上游工程在做组件拆分时适用：

- 上游 `install(TARGETS ... EXPORT ...)` 针对全量 target；
- 构建系统存在 `$<TARGET_FILE:...>` 引用的可选/插件 target（codegen 插件最常见）；
- 源码来自 GitHub `archive/refs/tags/*.tar.gz`（**不含 git submodule**）且 `BUILD_TESTS` 会引用 `third_party/*`；
- 有 `*_PROVIDER=package` 之类的 provider 开关，使顶层 `find_package` 与交付 target 引用不重合。

不适用：上游本身就按组件拆好了（每个子目录独立 `project()` 且能单独 configure/install）；或交付目标就是全量。

## 输入输出定义

| 项 | 内容 |
|---|---|
| 输入 | 上游源码 tarball（含 pin 结论）；要交付的 target 名；上游 `CMakeLists` 中该 target 的 `target_link_libraries` 与公开头 `foreach(_hdr ...)` 列表 |
| 输出 | `conan create` 可复现的组件包：`lib<target>.a/.so` + 该 target 的公开头 + `LICENSE`；`requires` 仅为真正链接的包 |
| 关键中间物 | `conandata.yml`：主源 + 每个 `third_party` 子模块的 **pin commit tarball + sha256**；`package()`：手动 copy（不经上游 install） |
| 判据 | ① `-- Generating done` 且 `Build files have been written`（generate 无错）；② `cmake --build --target <t>` 成功；③ `conan create` 的 `test_package` 真跑通；④ `ldd`/`nm` 验证产物只依赖声明的运行期包 |

## 示例（本案例实测）

`libgpr 1.82.0`（grpc 1.82.0 的 `gpr` target，PR !13983）：

```bash
# ① 找 generate 期硬前提：BUILD_TESTS=ON 会引用 grpc_cpp_plugin
grep -n '\$<TARGET_FILE:' CMakeLists.txt | head
#   → 多处以 $<TARGET_FILE:grpc_cpp_plugin> 作为 add_custom_command 的 DEPENDS/COMMAND

# 错误现象（关掉 CODEGEN 时）：configure 完成后
#   -- Generating done
#   CMake Error at CMakeLists.txt:597 (add_custom_command):
#     Error evaluating generator expression: $<TARGET_FILE:grpc_cpp_plugin>
#     No target "grpc_cpp_plugin"
#   CMake Generate step failed.  Build files cannot be regenerated correctly.

# ② 修：选项耦合要满足上游假定，但只 build 需要的 target
#   tc.variables["gRPC_BUILD_CODEGEN"] = True   # 让 target 在 generate 期存在
cmake --build <build> --target gpr -j16      # 不列 grpc_cpp_plugin → 不真编它

# ③ 子模块物化（release tarball 里 third_party/* 是空的）
#   conandata: xds -> cncf/xds @ ee656c7534f5d7dc23d44dd611689568f72017a6 + sha256
#   source(): get(...); shutil.move(glob.glob('xds-*')[0], 'third_party/xds')

# ④ 依赖分层：判据不是「顶层 find_package 了谁」而是「交付 target 链接了谁」
awk '/add_library\(gpr/,/^\)/' CMakeLists.txt | grep -A40 target_link_libraries \
  | grep -oE 'absl::[a-z_]+' | sort -u | wc -l      # → 22（全是 abseil）
#   → requires 只写 abseil-cpp/20260107.1（transitive_headers）
#   → protobuf / c-ares / re2 / openssl / zlib 仅「配置期依赖」，不取符号

# ⑤ 交付验证
conan create archives/l/libgpr/1.82.0 -pr:h/-pr:b=ohos-aarch64-wsl --build=missing   # EXIT=0
#   ctest 1/1 Passed；上游 15 个 gpr 相关单测 57/57（100%）
```

## 查重差异表（与最相近条目逐条比）

| 条目 | 它讲什么 | 本条目差异 |
|---|---|---|
| `DRAFT-E998-boost-component-split-methodology` | Boost/Build 体系下用**手工 clang++ 编译**裁剪组件（b2 不可用），四步法：源清单/配方模板/依赖裁剪/测试选型 | 那条是 "构建工具不可用 → 手工编译"；本条目是 "CMake 工具链可用，但**上游构建前提按全量写死**，拆分时被 generate 期/install 期/子模块/依赖圈层四处绊住"，是 **CMake build-graph 层**的问题 |
| `DRAFT-itsy_bitsy-0.8-upstream-test-materialization` | 空 `vendor/` 子模块的**测试头文件**物化（header-only 包） | 重叠仅在「子模块为空」这一点；本条目把它作为四前提之一，且重心在 generate 期的 `$<TARGET_FILE:>` 与 install/依赖圈层 |
| `DRAFT-ohos-distro-subproject-standalone-packaging` | 发行版 tarball 内**多个库**（autotools `AC_CONFIG_SUBDIRS`）能否独立成包的**判据** | 那条判「能不能拆」，本条目判「拆了之后 CMake 构建前提怎么补齐」 |
| `DRAFT-grpc-component-rich-integration` | **消费端**：下游库集成 registry 的 rich-cmake grpc/protobuf 包（`cmake_find_mode=none` 的目标名桥接五件套） | 本条目是**生产端**（把上游拆成组件包），两者互补 |

## 验证证据

- PR !13983（`archives/l/libgpr/1.82.0/`）：`conan create` EXIT=0，`test_package` 6 断言全过；
- 上游 15 个 gpr 相关 gtest 程序 **57/57（100%）**，逐程序计数见
  `tasks/libgpr-1.82.0-2026-09-30/logs/001-upstream-tests.log`；
- 同手法已合入先例：`archives/l/libgrpc_unsecure/1.82.0`（其 manifest 的 `split_targets` 明确含 `gpr`）、`archives/l/libgrpc_authorization_provider/1.82.0`。

## 平台侧修法建议（若有）

- 若上游把「插件 target 是否存在」作为 generate 期硬前提，**优先用选项打开它**（保持上游假定成立），而不是去改上游 CMake 删掉 `$<TARGET_FILE:>` 引用——后者会让补丁随上游演进而失效；
- 「配置期依赖」建议在 `notes.md`/`manifest.yaml` 里显式标注（本项目已如此做），评审与后续消费者才能分辨运行期闭包与构建期闭包。