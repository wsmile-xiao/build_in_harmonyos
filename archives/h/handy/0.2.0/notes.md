# handy 0.2.0 适配笔记

## 上游
- https://github.com/yedf/handy tag 0.2.0（无 v 前缀！任务卡 url=yedf/handy）
- sha256=831d9e7cdf94d19fbc8438e75dc6c63fa75777ff2f83ac48df981c22e924a2d1
- 零外部依赖（仅 pthread），CMakeLists.txt 只 find_package(Threads)
- 双构建路径：CMakeLists（库）+ Makefile（leveldb 风格 build_config 检测 OS，含测试目标 handy_test）

## 平台差异
1. **DEFFILEMODE**（patches/0001）：glibc <sys/stat.h> 有，musl 没有。logging.cc 两处 open(..., DEFFILEMODE)。补丁 #ifndef 守卫定义 POSIX 模式位，glibc 不受影响。
2. SYS_gettid 在 OHOS musl 可用（syscall(SYS_gettid) 正常）。
3. CMAKE_HOST_UNIX 在 HarmonyOS 上为真 → OS_LINUX 分支正确（poller/port_posix 走 Linux API）。
4. Makefile 路线 TARGET_OS=Linux 强制走 Linux case（uname -s 返回 HarmonyOS 不在 case 里）。
5. 运行期：ELF 需签名（llvm-objcopy --remove-section .codesign + binary-sign-tool -selfSign 1）；LD_LIBRARY_PATH 需 /system/lib64（libc++_shared.so 运行态符号在系统真 so）。

## 上游测试（N=11）
grep '^TEST(' test/*.ut.cc = 11：
- conf.ut.cc: allFiles（用 test/files/*.ini fixtures，cwd 必须在源码根）
- handy.ut.cc: Ip4Addr（解析 www.baidu.com，需外网）、EventBase、Timer、TcpServer1、kevent
- tcpcli.ut.cc: tcpcli（连 www.baidu.com:80/81 + localhost:10000，需外网）
- threads.ut.cc: ThreadPool、SafeQueue
- util.ut.cc: static_func、ExitCaller

harness 输出 `==== PASSED <n> tests`，断言失败 abort。本机（OHOS worker）实测 11/11 全过（2026-09-19，含两个外网用例）。

## 配方要点
- CMake 路线打包 libhandy_s.a（上游默认 BUILD_HANDY_STATIC_LIBRARY=ON）；shared=True 时走 libhandy.so
- 上游测试在 build() 里驱动 Makefile 路线生成 handy_test 再执行（R34：test 实质依赖被测包）
- cmake target: handy::handy；system_libs pthread
