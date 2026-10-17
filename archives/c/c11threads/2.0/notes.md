# c11threads 2.0 适配笔记

## 编译环境

- 构建系统：上游 Makefile（仅用于构建测试程序）
- 编译日期：2026-10-04
- 编译器：Conan OHOS profile 提供的 clang
- 状态：built

## 版本与源码

上游 tag v2.0，官方 GitHub archive 格式 tarball，sha256 `20010fc867e78bcba3ac24ddb59765a5d74cb1ec7c447e10988f78f847bc543c`（本机同时从官方源与 ghfast.top 镜像下载，逐字节一致）。conandata.yml 中 ghfast.top 镜像在前、官方源兜底（ghfast 对 codeload 格式返回 403，必须用 archive 格式）。

## 库形态

c11threads 是 header-only 库：整个 pthreads 后端实现就是单个 `c11threads.h`（static inline 函数直接封装 pthread_create/pthread_join/pthread_mutex_*/pthread_cond_*/pthread_key_* 等调用）。上游另有 win32 后端 `c11threads_win32.c`，仅 `_WIN32` 生效，OHOS/Linux 平台不参与编译，不打包。

配方 `package_type = "header-library"`，`package_id` 清空（全 profile 单一 package），安装物仅 `include/c11threads.h` 与 `licenses/README.md`（上游无独立 LICENSE 文件，公有领域声明在 README.md 与头文件头部）。

## 适配方式

零补丁：OHOS musl libc 提供完整 pthreads API（含 pthread_mutex_timedlock、pthread_key_create、pthread_once），且 `time.h` 提供 C11 `timespec_get`（musl 已实现），上游测试源码无需任何修改即可在 OHOS 原生编译运行。

构建阶段 = 构建并运行上游测试程序：
- `make -C test -j1 CC=<conf 注入的 clang>`，上游 Makefile 固定 `-std=gnu11 -pedantic -Wall -g -I.. -lpthread`，仅注入 CC（R33：编译器从 `tools.build:compiler_executables` conf 获取，不用裸 `${CC}`）
- 运行 `test/test`：任一断言失败即 abort（非零退出），全过输出 `tests finished`

上游无 `make install`，package 阶段直接 copy 头文件。

## 依赖

- 无三方依赖（W0 检查通过）
- pthread：OHOS musl libc 系统库，pthread 符号在 libc 内；test_package 的 CMakeLists 显式 `find_package(Threads)` 以兼容 glibc Linux 的消费者场景

## 测试边界

- 上游：test/Makefile 注册单一测试程序目标 `test`（N=1 注册口径）；程序内部含 5 个功能测试组（thread create/join、timed mutex、condvar、TSS、call_once），61 个断言，全部执行通过（本机 HarmonyOS aarch64 原生跑通全绿）
- 适配补充：1 个 Conan 消费者集成测试 test_package/test_c11threads.c（16 个断言）：thrd_create 创建 4 线程 + thrd_join 等待并断言每线程返回值，覆盖 mtx/cnd/tss/call_once/thrd_equal/thrd_trylock；上游测试程序按 1 个集成场景计数，不拆分虚增

## 已知说明

- win32 后端不打包：`c11threads_win32.c` 仅 Windows 使用，validate() 限定 os 为 Linux/OHOS
- 上游测试中 `run_timed_mtx_test` 依赖 `timespec_get(TIME_UTC)`（C11），musl 已实现，无需 glibc 特有处理
- 上游无版本号 soname/库文件，无 commands.json 需求（纯头文件库）

---

**编译结束**: 2026-10-04
**最终状态**: built
