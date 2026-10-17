# Cling 1.3 适配笔记

## 基本信息

- 软件：Cling 交互式 C++ 解释器
- 版本：1.3
- 上游：https://github.com/root-project/cling
- 配套 LLVM：https://github.com/root-project/llvm-project/tree/cling-llvm20-20260119-01
- 适配日期：2026-07-18
- 产物类型：`cling` 命令行工具及 `libcling`

## 构建模型

Cling 不是独立 CMake 工程。配方按上游与 Homebrew 的同版本方案，把 Cling 作为
LLVM monorepo 的外部项目，与 Clang 一起构建：

```text
cmake -S llvm-project/llvm -B <build>
  -DLLVM_ENABLE_PROJECTS=clang
  -DLLVM_EXTERNAL_PROJECTS=cling
  -DLLVM_EXTERNAL_CLING_SOURCE_DIR=<cling source>
  -DLLVM_TARGETS_TO_BUILD=host;NVPTX
  -DCLING_CXX_PATH=clang++
```

完整执行由 `CMakeToolchain` 和 `CMake` helper 生成，编译器来自 Conan profile，
没有依赖裸 `${CC}`/`${CXX}` 环境变量。

GitHub API 核对 `v1.3` 为 annotated tag：tag object
`c2beed49284ba337683cc557e46509232d93603b` 解引用到源码 commit
`af630d98a4aff3868de049d528402a628da0830a`。Cling 源码补丁的 `Source-Commit`
使用解引用后的 commit，而不是 tag object。

配套 LLVM tag `cling-llvm20-20260119-01` 同样是 annotated tag：tag object
`098d99f75d99c15ab7ee0c45d9fd87f3200231c0` 解引用到 commit
`6fb92ab985353ed71faec49beaaf5d111e041f8c`。三个 LLVM 补丁均使用该真实源码
commit，并补齐 `Modification-Layer` 与 E007/E140 `Knowledge-Ref` 元数据。

## HarmonyOS 适配

### 1. LLVM 宿主平台识别

正式 profile 把 CMake system 映射为 `HarmonyOS`，但 LLVM 20 的
`HandleLLVMOptions.cmake` 只接受 Win32、Fuchsia、Unix 和 Generic；同时
`llvm/cmake/config.guess` 不认识 Worker 的 `uname -s = HarmonyOS`。两个补丁分别：

1. 将常见 HarmonyOS 架构映射为 `<arch>-unknown-linux-ohos`。
2. 将 `CMAKE_SYSTEM_NAME=HarmonyOS` 归入 LLVM 的 Unix-like 分支。

Conan CI 使用 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 没有对应平台模块，因此内建
`UNIX` 变量仍为空。Cling 的 `lib/Interpreter/CMakeLists.txt` 用 `if(UNIX)` 同时
控制 `Exception.cpp`/`Interpreter.cpp` 的局部 exceptions 选项和 C++ 头路径探测。
配方只在 OHOS 下设置 `UNIX=ON`，与官方 OHOS SDK toolchain 的做法一致；没有对
完整 LLVM/Clang 全局启用 `LLVM_ENABLE_EH` 或 `LLVM_ENABLE_RTTI`。

恢复 `UNIX` 后，LLVM `AddLLVM.cmake` 还会给显式共享目标设置 `VERSION` 和
`SOVERSION`，从而为 `libcling`、`libclingJupyter` 生成版本化真实库和无版本软链。
E050 已记录 HMDFS 无法可靠创建或跟踪共享库软链。第四份补丁仅在官方 SDK 使用的
`CMAKE_SYSTEM_NAME=OHOS` 或 Conan CI 使用的 `HarmonyOS` 映射下跳过这两个属性，
使每个目标直接生成一个无版本真实 `.so`；其他 Unix 平台继续保留上游 SONAME 规则。

### 2. 可选依赖边界

首轮配方关闭 libedit、libxml2、zlib、zstd、curl、FFI、libpfm 和 Z3 等可选能力。
其中 libedit/ncurses 当前只有旧归档、没有可用 Conan recipe；仓库 zstd recipe 的
CMake target 名也与 LLVM 20 预期不一致。核心解释、Clang 前端、ORC JIT 和脚本
执行不依赖这些可选库。本包因此没有第三方 Conan 依赖，只有 libc/libc++、线程和
动态加载等平台接口。

Cling 使用 Clang 的 C++ 组件库，不消费独立的 libclang C API。Clang 默认仍启用
`CLANG_TOOL_LIBCLANG_BUILD`，该目标会自行设置 `VERSION` 并绕过 LLVM 通用共享库
属性补丁，在 HMDFS 生成 `libclang.so.20.1.8 -> libclang.so`。配方显式关闭该无关
目标，并同步关闭只为 libclang C API 测试服务的 `c-index-test` 与 `c-arcmt-test`。
后两者若单独保留，会把已关闭的 CMake 目标静默降级为裸 `-llibclang`，确定在链接
阶段失败。三个官方开关一起关闭后，既缩小构建闭包，也避免版本软链和悬空链接项；
Clang 前端、Cling 以及它们需要的静态组件目标保持不变。

### 3. 运行时 UserInterface 目标

Build #8327 在 94% 链接 `bin/cling` 时失败：

```text
old.lld: error: unable to find library -lclingUserInterface
```

这不是缺少 Conan 依赖。Cling v1.3 与当前上游 master 的 `lib/CMakeLists.txt` 都只在
`CLING_INCLUDE_TESTS=ON` 时进入 `lib/UserInterface`，但
`tools/driver/CMakeLists.txt` 在静态和共享构建中都会链接 `clingUserInterface`。
本配方为控制全量 lit 成本明确关闭测试，目标因此未定义；CMake 把
`target_link_libraries()` 中未解析的裸名称当作外部库名，最终生成
`-lclingUserInterface`。

`0003-cling-cmake-build-user-interface-without-tests.patch` 只把运行时组件移出测试条件，
不启用测试目录。Cling 与 LLVM 是两个独立下载到同一 source folder 的源码树，六个
补丁因此在 `conandata.yml` 分别声明 `base_path`，并由 Conan 标准
`apply_conandata_patches()` 按条目路由，避免把 Cling 补丁误应用到 `llvm-project/`。

### 4. OHOS 系统头路径发现

Build #9206 已完成配置、编译、安装、签名和打包，但消费者的标准库表达式以 139
退出。真机分层诊断确认 `--version` 与 `-noruntime` 的 `puts` 均通过，而任何默认
运行时输入都会先报：

```text
fatal error: 'features.h' file not found
Signal 11 (core dumped)
```

系统 `clang++ -xc++ -E -v /dev/null` 实际返回 libc++、Clang resource headers、
架构 sysroot 和通用 sysroot 四类目录。Cling 上游的配置期和运行时查询却只保留路径
名中含 `++` 的目录，因此仅留下 libc++，丢弃
`sysroot/usr/include/aarch64-linux-ohos` 与 `sysroot/usr/include`。缺失
`features.h` 是首错，Signal 11 是 Cling 在致命解析错误后的二次崩溃，不是 ORC JIT
或可执行内存策略的首因。

第五、六份补丁分别处理配置期与运行时回退查询。配置期仅在 `OHOS/HarmonyOS` 下
额外保留两级 sysroot 系统头，并把私有 `CLING_OHOS_SYSROOT_MERGE` 定义到 LLVM
实际创建、实际编译 `CIFactory.cpp` 的 `obj.clingInterpreter` 对象目标；运行时由该
配置特性宏选择补合并分支，先保留相邻编译器发现顺序，再从 `CLING_CXX_INCL` 追加
缺失的绝对 sysroot 路径。比较前去除尾 `/`，避免同一目录重复；
相对路径和非 sysroot resource 路径不进入补合并。相邻结果为空时仍走上游 fallback，
Linux 分支继续使用上游查询。OHOS 的 sed 表达式用 `[+][+]` 表示字面 `++`，兼容目标
环境的基本正则实现。

该修复直接覆盖“相邻 clang 返回非空但不完整结果并遮蔽完整 fallback”的 P1。真机
重新配置生成的 `CLING_CXX_INCL` 包含 libc++ 和两级 sysroot；源码候选 SHA-256 为
`a07fb914...` 与 `ae466d6b...`。真实 `compile_commands.json` 中 `CIFactory.cpp` 的
1/1 编译命令包含该宏，宏的 38 个编译项均位于 `lib/Interpreter`；独立 CMake 路由
夹具验证 `OHOS/HarmonyOS/Linux` 为 3/3，前两者定义、Linux 不定义。签名 ELF 夹具对
完整 sysroot、仅 libc++、空发现、尾斜杠去重和含空格路径共 5 组全部通过，每组输出
`E238_RESULT=42` 并逐项核对路径
顺序。随后签名 package 以 `LD_LIBRARY_PATH=<package>/lib` 独立运行 52 个 C++17
消费者和 1 个版本入口，结果为 53/53；另从完整构建树执行
`cmake --install --component libcling`，以安装产物编译、签名并运行 1 个嵌入式消费者，
组合结果为 54/54。

### 5. 安装布局和 ELF 签名

Cling 根据真实可执行文件位置寻找 `lib/clang/20` resource headers，故使用完整
`cmake --install`，不把 `bin/cling` 单独复制或改成符号链接。`package()` 扫描
`bin/` 和 `lib/` 的 ELF magic，跳过脚本、静态归档和符号链接；OHOS Worker 上
通过独立临时输出移除旧 `.codesign`，原子替换后再用 `binary-sign-tool` 自签。
该流程对没有 `.codesign` 的新 ELF 也是幂等的，且不会在 objcopy 中断时原地损坏
包文件。`package()` 必须先完成 ELF 签名；签名失败会在进入 `test_package` 前阻塞
`conan create`。

该包同时交付 CLI 和可公开链接的 `libcling`，因此 Conan 包类型使用
`shared-library`，并导出 CMakeDeps 目标 `cling::cling`；`bindirs` 仍保留 CLI 的运行时
契约。`test_package` 必须实际通过该目标编译 embedding 消费者，不能只执行命令行工具
后就宣称头文件和共享库接口可用。

## 测试

上游测试入口是 `check-cling`，源码树共有 262 个测试相关文件。该套件会执行构建
树中的 Cling、Clang、FileCheck 和插件，既依赖大体量 LLVM 测试工具，也受 OHOS
构建树 ELF 签名限制。首轮 PR 不在 `build()` 中启用完整 lit 套件，以避免超出
正式 CI 的可重复时间边界；该限制在 `test_package/MANIFEST.yml` 中显式记录。

消费者测试新增并执行 54 个独立入口：

1. 1 个包内 `cling --version` 进程，按上游实现精确核对输出 `1.3`，不臆测品牌前缀。
2. 52 个由 `smoke.sh` 分别启动的 Cling 功能进程；每项使用独立 C++17 输入、退出码
   和精确输出判定，覆盖标准容器、值类型、智能指针、函数对象、算法和数值算法。
3. 1 个链接 `cling::cling` 的嵌入式消费者进程，调用 `cling::Interpreter` 和
   `cling::Value` 求值 `6 * 7`；解释器有效性、求值状态和结果是同一入口内的三个
   独立失败判定，不拆成多个用例。

这些入口不是把同一断言拆分充数，也不重复 shared/static。原安装包日志包含 52 条
`[pass]`、0 条 `[fail]`、唯一 `CLING_MATRIX_RESULT=52/52`，版本入口为 1/1，合计
53/53；52 项矩阵日志 SHA-256 为
`74d98018859ec14e9d7eef4a0ba9a90e10ef68691355770ef2d423a7f9f5a792`，版本日志为
`b6403da9b22abe355ad17208a336e658322c5d1d7ff646ca7b9229237ba4aef4`。新增 embedding
日志为 1/1、三个失败判定为 3/3，并且消费者与 `libcling.so` 均含 `.codesign`，
SHA-256 为 `f3afa5d3021f70b08d1b7acbf389465b9239cf215fe86b35531ccce41591e4e1`；
两份日志组合为 54/54。
上游 207 个含 `RUN:` 的 lit 文件仅完成源码清点，未在 OHOS 上执行，仍记 0/207。
5 组 P1 编译器路径夹具复用同一消费者表达式，只作为定向回归，不重复计入 54 项。

## 本地与 CI 证据边界

两个官方源码包已在 E 盘下载并以 SHA-256 复核。Windows 本地完成源码布局、补丁
上下文、配方静态检查，并用 OHOS SDK Clang 15/CMake 3.28.2 成功生成完整 CMake
构建图：Clang 20.1.8、Cling 1.3、AArch64 与 NVPTX 目标均被识别。该配置检查显式
提供了 `LLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos`，且本地 SDK 对 C++ 头路径
仍有警告，因此它只证明源码与 CMake 接线正确，不证明正式 Worker 的宿主探测、
运行时头文件或 JIT 可用。

Windows 与 Ubuntu-D 仅用于官方源码 SHA、`git apply` 和 GNU patch 2.7.6
`--fuzz=0` 重放；Linux/x86_64 全量 LLVM 构建不能证明 OHOS/aarch64 的 JIT、W^X、
SELinux 或签名行为，因此不以宿主构建替代真机。运行时结论来自签名 OHOS package；
当前修复提交后的正式 CI 仍须按新 HEAD 重新执行。

首个正式 Build #8072 在 LLVM/Clang 已构建到 83% 后，于 Cling `Exception.cpp`
报 `cannot use 'throw' with exceptions disabled`。日志证明双源码、两份补丁和大部分
LLVM 构建均已通过；根因是 `HarmonyOS` 未定义 CMake 的 `UNIX`，导致上游局部
`-fexceptions/-frtti` 分支未执行。本次按上述 `UNIX=ON` 修复。此前按 AI Review
使用显式 `patch(..., base_path="llvm-project")` 保住补丁门禁；新增 Cling 源树补丁后，
又按 Conan 2.29.1 `patches.py` 核验结果改回标准 `apply_conandata_patches()`，并把
根目录移到每条 conandata patch 的原生 `base_path` 字段，支持两个源码根且不绕过门禁。

第二个正式 Build #8327 对完整 HEAD
`30421c34f660f11eaee41b9271242d75761f410b` 构建 4983 秒，LLVM/Clang/Cling
编译已到 96%，该日志中的唯一致命错误是上述缺失 `clingUserInterface` 目标。
Buildbot API 报告日志共 4689 行；本次修复后需由新 HEAD 的正式 CI 重新验证完整
链接、安装、签名和消费者测试。

新 HEAD 的独立 W4 进一步检查生成目标图时发现，`UNIX=ON` 会让 `libcling` 和
`libclingJupyter` 各产生一条 `CMAKE_SYMLINK_LIBRARY` 规则。该问题在 Build #8327
的失败点之后，旧日志不能证明安全。第四份补丁应用后重新配置必须确认这两类规则
均为零，再进入新的独立 W4；该预防性修复复用既有 E050，并把 E140 从仅匹配
`HarmonyOS` 完善为同时覆盖官方 SDK 的 `OHOS` 与 Conan 工具链映射，不新增重复条目。

随后 W4 对完整 `all` 依赖图继续检查，发现默认 `libclang` C API 目标仍显式生成一条
版本软链，且 `cmake.build()` 和安装脚本都会触发。该目标不是 Cling 的依赖，现通过
官方 CMake 选项 `CLANG_TOOL_LIBCLANG_BUILD=OFF` 关闭。再次生成图后，W4 又发现
`c-index-test` 与 `c-arcmt-test` 仍在默认 `all` 中引用缺失目标并生成两处裸
`-llibclang`；现同步设置 `CLANG_TOOL_C_INDEX_TEST_BUILD=OFF` 和
`CLANG_TOOL_C_ARCMT_TEST_BUILD=OFF`。全新配置的最终目标图已确认三个目标均缺失、
裸 `-llibclang` 为零、全部 `CMAKE_SYMLINK_LIBRARY` 规则为零，并保留
`libcling`/`libclingJupyter` 两个无版本真实 `.so` 目标；该结果仍需重新执行独立 W4。

Build #8914 随后完成 LLVM/Clang/Cling 的配置、编译、安装、打包和 ELF 门禁，进入
`test_package` 后包内 `cling --version` 真实输出上游规定的 `1.3`。旧测试额外要求
输出包含 `cling`，因此把合法结果误判为失败，并在 JIT smoke 之前终止。现改为对
去除行尾空白后的输出与 Conan 已解析包版本做精确比较；该修改只修测试契约，不改
上游二进制。新 HEAD 仍需正式 CI 重新执行版本检查和 JIT smoke。

Build #9206 已继续通过配置、编译、安装、签名和打包，消费者默认运行时的第一条错误
是 `features.h` 缺失，随后才退出 139。该历史日志用于定位 P1，不能代表当前修复。
针对 Review 的形式争议，运行时四处平台守卫已改为 CMake 注入的项目私有特性宏；
定义必须落到 `obj.clingInterpreter`，不能落到只消费对象文件的表面目标。新候选已在
同一完整构建树中重新配置、编译和链接，configure/build 日志 SHA-256 分别为
`da6139ec...` 与 `fb35e45c...`，compile database 为 `29fd2d71...`。全新签名 package
的 5 组定向回归为 5/5，52 项功能
矩阵与独立 `--version` 入口合计 53/53；正式安装的 `libcling.so` embedding 入口另为
1/1，组合为 54/54。当前修复后的正式 CI 仍待新 HEAD 执行。

## 新增通用知识

提交前已搜索云端 `knowledge/graph`、`knowledge/doc` 和 `knowledge/operations`。
E050/E191/E208 及链接调试文档都把 `-lxxx` 解释为真实外部库、搜索路径或 libc 问题，
没有覆盖“CMake 内部目标被条件排除后静默降级为 `-l<target>`”的根因；现有文档也
没有说明多源码 recipe 的补丁应通过 `conandata.yml` 的逐条 `base_path` 路由；也没有
覆盖 CLI 版本测试臆测品牌前缀、从而拒绝生产者合法纯版本输出的测试契约错误。

- E140 知识草稿更新：CMake 平台路由同时匹配 `OHOS|HarmonyOS`，避免本地 SDK 与
  Conan CI 静默进入不同分支；需把项目私有特性宏定义到真正编译源码的对象目标，
  并从 compile database 回读，不能只凭表面 target 名推断宏已生效。
- E215 知识草稿：先核对 `if(TARGET ...)`、条件 `add_subdirectory()` 和生成目标图，再决定
  是否增加包依赖或 `-L`。适用于所有含可选组件/测试开关的 CMake 工程。
- E216 知识草稿：多个源码包共存于 Conan `source_folder` 时，每个补丁声明自己的
  `base_path`，由标准 `apply_conandata_patches()` 应用。适用于主源码加配套源码、
  vendored 依赖或工具链源码的 recipe。
- E235 知识草稿：`--version` 断言先核对生产者文档或源码定义，再按真实契约解析和
  比较；禁止把产品名、品牌前缀或额外描述当成未经证实的必需输出。适用于所有 CLI
  工具的 Conan 消费者测试和 CI smoke。
- E238 知识草稿：嵌入式 Clang 从宿主编译器输出提取 C++ 头路径时，OHOS 还必须
  保留架构与通用 sysroot 系统头；相邻编译器结果非空也不能代替完整性检查。修复按
  稳定顺序补齐绝对 sysroot、归一化尾斜杠，并保持 Cling resource headers 与目标
  sysroot 的版本边界；5 组签名 ELF、53 个 package CLI 入口和 1 个 `libcling`
  embedding 入口共同验证该模式。

E140 更新和四条新增知识目前均为 `knowledge/graph/draft/` 下配套 `.kv/.md` 草稿，
随 Cling 软件正式 PR 一起提交；它们不是正式知识，也未同步正式索引。草稿提供
Build #8327/#8914/#9206、上游 CMake/Interpreter 源码、官方 Conan 2.29.1
`patches.py` 行为、本地生成目标图、真机 5/5 定向回归和 54/54 组合日志作为
复用证据，因此本任务适配路径应备注为路径 A+B+C。

Build #10938 的两个源码包均下载成功，Ninja 也完成了默认 `all` 目标的 3706/3706，
但整个 `conan create` 在约 6050 秒处被 CI 总时限终止。机器人摘要中的
`[429/3706]` 是 Ninja 进度，不是 HTTP 429。默认 `cmake.build()` 会构建大量不属于
Cling 制品合同的 LLVM/Clang 工具和 fuzzer；完整 `cmake.install()` 又要求这些目标均
已生成。现改为只构建 `cling`、`libcling` 和 Cling/Clang/LLVM/resource headers 六个
目标，并通过显式 CMake component 安装相同的 CLI、共享库与头文件布局。该收窄不改变
`bin/cling`、`lib/libcling.so`、公开头文件或 `lib/clang/20/include` resource headers
合同，仍由原有 CLI/JIT 和 embedding 消费者验证。

## 高难度挑战说明

该任务命中路径 C 的以下判定项：

- 配套构建完整 LLVM 20 + Clang + Cling，依赖图和制品规模大。
- Cling 使用 ORC JIT 与可执行内存，受 OHOS W^X/SELinux/签名策略影响。
- 上游 lit 回归测试需要多个构建树工具，全量验证成本高。
- Cling 与特定 LLVM tag 强绑定，不能复用仓库现有旧 LLVM 归档。

当前状态为 `built`：相邻 `clang` 非空不完整结果遮蔽 fallback 的 P1 已修复，完整
真机重编译、签名 package、5/5 定向回归和 54/54 新增入口均通过。上游 207 项未执行，
仍真实记录为 0/207；当前修复提交后的正式 CI 尚未运行，因此不能标记为 `published`。
