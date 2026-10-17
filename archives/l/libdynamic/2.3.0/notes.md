# libdynamic 2.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18) / clang++
- 平台: HarmonyOS aarch64 (HongMeng Kernel 1.12.0, musl 系 OHOS libc)
- 状态: built

## 编译步骤

1. 源码: https://github.com/fredrikwidlund/libdynamic (官方 tag v2.3.0)
   本机 github.com 直连超时，经 codeload.github.com 官方归档下载 tar.gz。
2. `bash autogen.sh` (autoreconf --force --install) 生成 configure。
3. `./configure --prefix=$DEFAULT_PREFIX` (DEFAULT_PREFIX=/storage/Users/currentUser/usr/local)
4. `make -j1`
5. `make check -j1`（上游测试，需要 cmocka/2.0.2：`conan download cmocka/2.0.2 -r=ohpcd`，
   CPPFLAGS/LDFLAGS 指向本机 conan 缓存包目录）
6. `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别平台 / config.status 临时目录 Permission denied | ① config.guess 不含 HarmonyOS 分支；② 本机 HMDFS 对 `umask 077 && mktemp -d` 生成的 0700 目录不授予当前用户写权限（E046 类平台限制） | ① config.guess 增加 `*:HarmonyOS:*:*` → echo `aarch64-unknown-linux-ohos`（E007 范式）；② configure/config.status 临时目录改为 `mktemp -d`（默认 umask）+ `mkdir -m 0777` 后备（abook 同款） |
| 2 | 生成的 libtool 报 `X--tag=CC: inaccessible or not found` | 环境 libtool 为混合安装（libtoolize 2.4.7 包装 + 自带 ltmain.sh 为 1.5.22），生成的 libtool 未初始化 `$echo`（小写），参数被当命令执行 | ltmain.sh 增加 `echo="$ECHO"` 初始化（源码级，再生成不丢） |
| 3 | `ranlib ` 空参数报错 | 2.4.7 配置段使用 `$tool_oldlib`，1.5.22 主体未定义该变量 | configure/config.status/libtool 三处 `$tool_oldlib` → `$oldlib` |
| 4 | make 触发 Makefile.in 再生成时缺 automake aux 文件 | libtoolize --force 后 aux 文件被清理 | 从 automake-1.16 share 目录补装 compile/missing/depcomp |
| 5 | make check 链接失败 `undefined symbol: pthread_cancel` | OHOS 工具链 libc 不提供 `pthread_cancel` 符号（musl 系裁剪） | pool.c 改为消息式/关闭式退出：worker 线程 `recv()<=0` 即退出；pool_destruct 用 `shutdown(socket_master)` 唤醒 + `pthread_join`；send 加 `MSG_NOSIGNAL` 防 EPIPE |
| 6 | 测试链 pool 子用例 SIGPIPE(141) | shutdown 对端后 worker send 触发 SIGPIPE | send 改用 `MSG_NOSIGNAL` |
| 7 | test/coverage.sh 失败 | 环境无 gcov 工具（`gcov: inaccessible or not found`） | 平台工具缺失，覆盖率检查无法在本环境运行，不影响编译/其余测试 |

## 源码修改

- `autotools/config.guess`: 添加 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`（E007 范式）
- `src/dynamic/pool.h`: 添加 `#include <pthread.h>`（头文件自包含，pool.h 使用 pthread_t）
- `src/dynamic/pool.c`: 移除 `pthread_cancel` 依赖：
  - pool_thread: `recv() <= 0` 即退出；send 增加 `MSG_NOSIGNAL`
  - pool_receive: POOL_MESSAGE_WORKER 仅 `pthread_join`
  - pool_destruct: `shutdown(socket_master)` 唤醒 worker 后逐线程 `pthread_join`
  - pool_send: send 增加 `MSG_NOSIGNAL`
- 生成文件修复（不入补丁，由配方 build() 复现或环境条件）：configure/config.status 的临时目录 `umask 077`（→ mktemp 默认 / mkdir -m 0777）、libtool 的 `$tool_oldlib`（→ `$oldlib`）、ltmain.sh `echo="$ECHO"` 初始化

## 依赖版本

- cmocka/2.0.2（仅测试期需要，从 ohpcd 制品仓拉取本机缓存）
- 运行时无第三方依赖（仅 libc/pthread/socket/epoll）

## 验证结果

```bash
make check -j1 # 14 用例（12 单元测试 + coverage.sh + valgrind.sh）
# PASS: 13/14（test/segment utility hash buffer list vector string maps mapi map pool core 全部通过；
#        test/valgrind.sh 通过；test/coverage.sh 因本环境无 gcov 无法运行）
```

## 注意事项

- 本机 gitcode/go-git 等远端能力待 PR 阶段使用；本笔记仅记录本地适配过程。
- 上游测试依赖 cmocka，测试构建需注入 `CPPFLAGS=-I<cmocka-cache>/include`、`LDFLAGS=-L<cmocka-cache>/lib -lcmocka`。
---

**编译结束**: 2026-09-22 17:10
**最终状态**: built
