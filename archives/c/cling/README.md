# Cling

Cling 是 ROOT 项目维护的交互式 C++ 解释器，基于 LLVM 和 Clang 提供即时编译、
表达式求值、脚本执行和嵌入式解释器能力。

## 功能概述

- 交互执行 C++ 声明、语句和表达式。
- 运行 `.cpp`/`.C` 脚本并动态加载 C/C++ 代码。
- 提供 `libcling`，供应用嵌入解释器。
- 使用 Clang 前端和 LLVM ORC JIT 生成本机代码。

## OHOS 适配

- Cling 1.3 必须与上游指定的 `cling-llvm20-20260119-01` LLVM/Clang 源码配套构建。
- LLVM 20 的宿主探测尚不识别 `HarmonyOS`，配方为 `config.guess` 和
  `HandleLLVMOptions.cmake` 添加最小平台识别补丁。
- Conan 生成 `CMAKE_SYSTEM_NAME=HarmonyOS` 时显式恢复 `UNIX=ON`，使 Cling 使用
  上游的局部 exceptions 配置和 Unix C++ 头路径探测；不会为整个 LLVM 全局开启 EH。
- 上游把运行时必需的 `clingUserInterface` 目标误放在测试开关内；配方保持测试关闭，
  但通过源码补丁始终定义该目标，避免 CMake 把内部目标名降级为裸 `-l` 链接项。
- Build #9206 的消费者默认运行时首先报告 `features.h` 缺失，随后退出 139；该顺序
  证明首因是 OHOS sysroot 系统头未进入嵌入式 Clang 搜索路径，而不是 JIT 内存策略。
- 第五、六份补丁分别处理配置期和运行时头路径发现。OHOS 运行时保留相邻 `clang`
  的发现顺序，再从 `CLING_CXX_INCL` 补齐缺失的绝对 sysroot 路径；空结果继续使用
  上游 fallback，Linux 查询保持不变。
- CMake 同时识别 `OHOS` 与 `HarmonyOS`，并把私有
  `CLING_OHOS_SYSROOT_MERGE` 特性宏定义到实际编译 `CIFactory.cpp` 的
  `obj.clingInterpreter`；Linux 不定义该宏，保持上游运行时查询。
- 构建关闭 libedit、libxml2、zlib 和 zstd 等可选功能，避免隐式使用 OHOS 系统库
  或未发布的 Conan 依赖；核心解释、JIT 和脚本执行能力保留。
- 安装保留完整前缀布局。不能把 `bin/cling` 改成指向其他目录的符号链接，否则
  Cling 无法按相对位置定位 Clang resource headers。
- `package()` 在 OHOS Worker 上通过临时文件清理旧 `.codesign` 后，对安装后的
  真实 ELF 可执行文件和共享库自签，随后 `test_package` 才执行解释器烟雾测试。
- `test_package` 执行 52 个独立 Cling 功能进程、1 个 `--version` 入口和 1 个链接
  `cling::cling` 的嵌入式消费者。真机组合日志已达到 54/54；另以 5 组签名编译器夹具
  覆盖完整、部分、空结果、尾斜杠和含空格路径，这 5 组不重复计入 54 个消费者入口。

## 依赖关系

- 构建工具：CMake、Clang/Clang++、Python。
- 配套源码：root-project/llvm-project `cling-llvm20-20260119-01`。
- 第三方 Conan 依赖：无。libc、libc++、线程和动态加载接口由 OHOS 平台提供。

## 参考资料

- 官网：https://root.cern/cling/
- Cling 源码：https://github.com/root-project/cling
- LLVM 配套源码：https://github.com/root-project/llvm-project
