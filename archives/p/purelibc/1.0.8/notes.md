# purelibc 1.0.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS clang 15.0.4，target aarch64-unknown-linux-ohos，/data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

conan create 全流程（OHOS 原生构建，build=host=OHOS/armv8）：

```bash
export CONAN_HOME=$HOME/tmp/ch/home-glm61
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
export PATH=$HOME/.local/bin:$PATH
cd ~/qzy/glm61-purelibc-1.0.8
conan create archives/p/purelibc/1.0.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
python3 scripts/ohc-run.py conan-verify purelibc 1.0.8   # milestone: conan_verify_passed
```

源码 URL：https://github.com/virtualsquare/purelibc/archive/refs/tags/1.0.8.tar.gz
（tag 1.0.8 经 `git ls-remote --tags` 核实；sha256 4c79969c...415ac6；codeload 等价源已登记 conandata）
初次下载走共享 download_cache（~/tmp/ch/dlcache，s/<sha256>+sidecar），绕过 github.com 直连超时。

## W0/W0b

- W0 依赖检查：上游无任何外部依赖（preflight_check.sh 报"无依赖需要检查"，conandata 无 requires）。✅
- W0b 历史经验：归档树无 purelibc 历史配方（recipe-search 语料 5594 条无命中），无历史 notes。✅
- 语言/构建预检：C 语言 + CMake（cmake_minimum_required 3.13），与任务声明（cpp 描述、单构建系统 cmake）匹配，无 env_unsupported 风险。✅

## 测试账本（五维）

| 项 | 值 | 说明 |
|---|---|---|
| N_static（上游静态用例） | 0 | 上游 tarball 无测试目录，CMakeLists.txt 无任何 add_test/测试目标（grep TEST 0 命中） |
| N_registered | 0 | 同上，构建系统无注册测试 |
| N_executed | 0 | 无可执行上游测试；build() 内如实不执行任何上游测试 |
| 未执行分类 | 0 | 无 |
| N_consumer（消费者测试程序） | 2 | purelibc_capture_test（系统调用截获链路断言）、purelibc_parse_mode_test（fopen 模式解析断言），真实调用公开 API 并 assert，设备上运行通过 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_library(LIBDL dl) NOTFOUND | OHOS sysroot 无 libdl.so（dl* 在 libc 内） | 补丁 0001：改用 CMAKE_DL_LIBS |
| 2 | dir.c：getdents64/readdir64/scandir64 重定义冲突 | musl dirent.h 把 *64 别名成 32 位名宏 | 补丁 0002：检测到别名宏时 #undef 并前向声明 readdir64；__off_t → off_t |
| 3 | socketcalls.c：__SOCKADDR_ARG 等未定义 + sockaddr_storage 重定义 | glibc 内部宏缺失；linux/socket.h 与 sys/socket.h 结构体重复定义 | 补丁 0003：musl 下定义兜底宏、内核头包含期间改名绕开 |
| 4 | stdio.c：*64 宏别名冲突、stdout=const 不可赋值 | musl stdio.h/fcntl.h LFS 别名；musl 标准流是 RELRO 常量指针 | 补丁 0005：别名 #undef；标准流重指派（PUREFLAG_STD*、_pure_freopen）在 musl 下降级 |
| 5 | syscalls.c：bits/wordsize.h 缺失、__GNUC_PREREQ 未定义、_STAT_VER_LINUX 走错分支、__off_t/__ssize_t 等缺失、mremap/ptrace/prlimit 签名冲突 | 一组 glibc 私有头/内部类型/枚举签名在 musl 缺失 | 补丁 0004：按 ABI 派生 __WORDSIZE；__GNUC_PREREQ 由编译器宏派生（走现代 stat 分支）；typedef/宏补齐；mremap 改 musl 兼容变参签名；ptrace/prlimit 枚举参数按 musl 用 int |
| 6 | 消费者测试 fclose 失败（退出码 4） | **OHOS musl fopencookie 行为偏离**：cookie 回调不在 fclose 内同步触发（延迟到进程退出）、close 回调从不触发、fclose 返回 -9（EBADF）——独立探针（不经 purelibc）复现 | 平台限制，非配方缺陷。补丁 0005：OHOS 上 stdio 覆盖层（fopen/fdopen/tmpfile/freopen 系）回退 libc 真实现（dlsym RTLD_NEXT）；消费者测试改用纯 syscall 截获层（open/write/close 包装器直调），glibc/musl 行为一致 |

## OHOS musl fopencookie 平台限制（证据）

独立探针（~/tmp/uc2/glm61/cookie-probe2.c，不经过 purelibc）：fopencookie(0x1234,"w",{NULL,cw,NULL,cc})，
fwrite 5 字节 + fclose：cw 回调确实收到正确 cookie（MATCH），但两次触发均发生在 fclose 返回 -9 之后
（进程退出阶段），cc（close 回调）从不触发。结论：OHOS musl 的 fopencookie 无法承载 stdio 虚拟化。
上游 1.0.10 的 stdio.c 与 1.0.8 无实质差异（diff 仅空白与 glibc 2.39 fileno 兼容），即上游未修此路径。
本次适配的降级范围（仅 OHOS）：stdio FILE 层回退 libc；系统调用截获核心（_pure_start + syscalls.c/direct.c/
socketcalls.c 包装器）完整可用并经消费者测试验证。

## 源码修改

- patches/0001-CMakeLists.txt.patch：CMAKE_DL_LIBS 替代 find_library(dl)（portability）
- patches/0002-dir.c.patch：musl dirent *64 别名 #undef + readdir64 前向声明 + off_t（portability）
- patches/0003-socketcalls.c.patch：musl socket 参数宏兜底 + 内核头 sockaddr_storage 改名绕开（portability）
- patches/0004-syscalls.c.patch：LFS 别名 #undef、__GNUC_PREREQ/__WORDSIZE 派生、__off_t 系 typedef、
  mremap/ptrace/prlimit 签名 musl 化（portability）
- patches/0005-stdio.c.patch：*64 别名 #undef、标准流重指派 musl 降级、fopencookie 系 stdio 覆盖在 musl
  回退 libc dlsym（portability + 平台限制降级）

## 依赖版本

无（零依赖包）。

## 验证结果

```bash
conan create ... --build=missing
# ... [100%] Built target purelibc_capture_test / purelibc_parse_mode_test
# ======== Testing the package: Executing test ========
# RUN: ./purelibc_capture_test      → exit 0
# RUN: ./purelibc_parse_mode_test   → exit 0
conan-verify → milestone: conan_verify_passed
```

消费者测试断言链：open("/mem/virtual.txt") 经 purelibc open 包装器被截获为 __NR_openat(AT_FDCWD) 返回
虚拟 fd；write(fd) 字节流进入处理器内存后备存储并计数；close 返回 0；其余系统调用经 _pure_start 返回的
原始 syscall 指针旁路转发。

## 注意事项

- OHOS 上 PUREFLAG_STD* 标准流截获与 fopen/fdopen 系 FILE 虚拟化不可用（musl fopencookie + 常量
  标准流限制），direct syscall 截获不受影响；glibc 上行为与上游完全一致（所有改动均 #if 门控）。
- github.com 直连超时时：codeload.github.com 可达；tarball 已预置共享 dlcache（含 sidecar 登记
  官方 URL）。
---

**编译结束**: 2026-09-20 03:13
**最终状态**: built
