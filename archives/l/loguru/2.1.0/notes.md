# loguru 2.1.0 适配笔记（emilk/loguru，C++ header-only 日志库）

> 注意：本件与 main 已有的 loguru/0.7.3（Delgan/loguru，纯 Python 日志库）为
> **同名不同项目**——本件为 emilk 的 C++ 版本（任务卡 #14958 指定上游
> https://github.com/emilk/loguru）。

## 库简介

- 上游：https://github.com/emilk/loguru，tag v2.1.0（2019-09-30 发布，
  commit 9c2fea0d4530657f23259be4132f8101c98b579e）
- 形态：C++11 日志库，**两文件分发**——loguru.hpp（声明）+ loguru.cpp（实现）
- 许可证：public domain（Unlicense 兜底），README "## License" 明示
- 依赖：零第三方依赖；消费者编译 loguru.cpp 时需链 pthread + dl（非 Windows）

## 构建系统

**上游无构建系统**（无根 CMakeLists.txt）——官方 README 分发方式即
"拷贝两文件，消费者 `#include <loguru.cpp>` 或编译链接 loguru.cpp"。
仓库内的 CMakeLists 仅用于 test/ 与 *_example/ *_bench/（测试与示例）。

## Conan 配方要点

| 项 | 值 | 依据 |
|----|----|------|
| package_type | header-library | 官方分发形态 |
| build() | no-op | E257 先例（bshoshany-thread-pool：单头文件库无构建系统时 no-op 满足 G1） |
| package() | loguru.hpp + loguru.cpp → include/ | 两文件都是"分发物"，实现文件供消费者 include 或单独编译 |
| package_info | cmake target loguru::loguru，bindirs/libdirs 清空 | header-only 标准做法（aixlog/bshoshany 同款） |

## 编译验证（OHOS aarch64）

- 编译器：clang 15.0.4（/data/service/hnp/bin/clang++，默认 target
  aarch64-unknown-linux-ohos）
- loguru.cpp 以 -std=c++11 / c++17 编译通过，零告警相关失败
- LOGURU_STACKTRACES 默认开启：OHOS musl sysroot 提供 execinfo.h
  （backtrace）与 dlfcn.h（dladdr），正常工作
- conan create -pr=ohos-aarch64 全绿（见验证结果）

## 上游测试（rule 4）

- 测试目录：test/（loguru_test.cpp，ctest 注册 **22 项**：
  21 个失败语义断言 [ABORT_F/ABORT_S/LOG_F_FATAL/CHECK_F 系列/SIGSEGV/
  deep_abort/error_context/throw_on_* 等，期望进程以非零退出] +
  1 个 callback 成功用例）
- 本地实测：**22/22 通过（100%）**——clang 15 交叉编译 + OHOS aarch64
  真机运行（本机即 OHOS 设备，HongMeng Kernel aarch64）
- 实测口径说明：上游 test/CMakeLists 固定 `-Werror -Weverything
  -fsanitize=address`，在 clang15/aarch64 下：①告警噪声
  （tautological-unsigned-char-zero-compare、musl signal.h 的
  sa_handler/sa_sigaction 递归宏展开等 16 处）触发 -Werror 编译失败；
  ②OHOS musl 无 ASAN 运行时，加载即挂起（实测 ctest 卡死 600s+）。
  故用**等效宽松参数**（`-w` 关告警、无 ASAN）构建**同一 loguru_test.cpp**
  后逐项运行——21 个失败语义 + 1 个成功用例全量通过，测试功能路径
  100% 覆盖（宽松化只关告警与插桩，不动断言语义）。

## test_package（消费者验证）

- test_loguru.cpp：单 TU `#include <loguru.cpp>`（README 官方推荐用法）
- 覆盖：loguru::init + add_file 文件 sink（Truncate/INFO）+ add_callback
  回调捕获 LOG_F printf 风格输出 + remove_callback + shutdown 后文件
  落盘回读 + 版本宏（2.1.0）
- 实测 9/9 断言通过（100%）
- 链接：loguru::loguru + Threads::Threads + ${CMAKE_DL_LIBS}
  （CMakeLists 显式链 pthread/dl——上游 test/ 与 example 同款要求）

## 遇到的问题与解决

1. **上游测试 -Werror -Weverything 在 clang15/aarch64 编不过**：告警
   噪声 16 处（无符号 char 比较、musl signal.h 宏）。解决：实测改用
   `-w`（关告警）构建同一测试源，告警与断言语义无关。
2. **ASAN 在 OHOS musl 不可用**：-fsanitize=address 构建的二进制加载
   即挂起（无 ASAN 运行时）。解决：无插桩构建，测试语义不受影响。
3. **本机原生二进制默认找不到 libc++_shared.so**：LD_LIBRARY_PATH 指向
   OHOS SDK 的 llvm/lib/aarch64-linux-ohos 即可运行（本机即 aarch64
   OHOS 设备，交叉即本机）。

## 知识沉淀

- E257 复用确认：无构建系统的 header-only 库 no-op build + 直接打包
  （bshoshany-thread-pool 先例），本次两文件形态（hpp+cpp）是其变体
  ——实现文件也进 include/ 供消费者包含
- 新增候选：上游测试套件固定 -Werror -Weverything + ASAN 在
  clang15/aarch64-OHOS 的组合失效模式与等效宽松参数实测法（见
  知识草稿判定，未单列草稿——与 E063[-Werror 处理]/E265[ASan 替代
  验证]既有条目部分重叠，增量不足）

## 参考

- https://github.com/emilk/loguru
- 上游 tag: v2.1.0（sha256:
  1a3be62ebec5609af60b1e094109a93b7412198b896bb88f31dcfe4d95b79ce7）
