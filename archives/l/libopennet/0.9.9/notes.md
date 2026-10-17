# libopennet 0.9.9 编译适配笔记

## 边界

- 本任务只处理 `libopennet/0.9.9`，目录落点 `archives/l/libopennet/0.9.9/`。
- 分支：`feat/libopennet-0.9.9`。
- 零外部依赖（纯 libc + POSIX/BSD sockets），无依赖闭包问题。
- License：opennet.c/opennet.h 为 LGPL-2.1-or-later，net.c 为 GPL-2.0-or-later。

## 上游信息

- 源码：`https://www.rkeene.org/files/oss/libopennet/libopennet-0.9.9.tar.gz`
- sha256（本地实测核对）：`d1350abe17ac507ffb50d360c5bf8290e97c6843f569a1d740f9c1d369200096`
- 构建系统：2004 年代 autoconf 2.59 风格 configure + 手写 Makefile.in
  （无 automake、无 libtool）。
- 产物：上游 Makefile 恒同时产出 `libopennet.a` 与 `libopennet.so`；
  conan `shared` 选项只决定消费者链接与打包内容（`.so` 重命名为
  `libopennet.so.0.9.9` + `so.0`/`so` 符号链接，镜像上游 install 布局）。
- 必须源内构建：`%_shr.o: %.c` 模式规则无 VPATH 支持，out-of-source
  make 报 "No rule to make target 'opennet_shr.o'"。

## 上游测试

**正式测试 0 个。** 上游 `make test` 只编译 test.c —— 它是无断言的
demo（打印指定文件内容，裸运行会未检查地解引用 argv[1] 而崩溃），
没有退出码语义，不算正式测试。按真实能力处理：配方在 build() 中
离线编译运行 test.c 作 smoke（静态链接刚构建的 libopennet.a，读本地
源码文件，显式 self.run），真实消费者覆盖在 test_package/。

## 源码补丁（两个，均有真实根因）

### patch 0001 — fseek_net 自递归 + length 未初始化

上游 opennet.c 两个真实 bug，不修复则任何真实消费者都会踩：

1. `fseek_net()` 调用了**它自己**而不是 `fseeko_net()` —— 第一次
   `fseek_net(..., SEEK_END)` 即无限递归 / 栈耗尽。
2. `fopen_net()` 声明 `off_t length;` 未初始化；本地文件路径下
   `open_net_internal()` 从不写 `*length`，栈垃圾流入
   `stream->length` 并传播进 `flength_net()`。

修复：`length = -1` 初始化 + 自递归改为调 `fseeko_net`。
注：本地文件的 `fseek_net(SEEK_END)` 修复后仍返回 -1（上游对本地
文件从不填 length，-1 是其确定性真实行为），test.c 断言的正是该
真实行为。

### patch 0002 — HMDFS + umask 077 导致 configure 临时目录不可写（E114）

configure 的 confstat 临时目录创建包在 `umask 077` 里：
`tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX")``。HMDFS 强制
目录 setgid，产出的 0700 目录即使属主是构建用户也不可写，config.status
报 `can't create ./confstatXXX/config.h` 之类 Permission denied。
修复：去掉 mktemp/mkdir 两行的 `umask 077` 包裹。

## OHOS 适配（知识库复用，路径 A，零新增 DRAFT）

全部复用既有知识条目，查重确认无新增：

- **E007**：2004 年代 config.guess 不识别 HarmonyOS → 显式
  `--build=aarch64-unknown-linux-gnu --host=...` 绕过探测
  （configure 全部探测为 AC_TRY_LINK 编译型，从不运行目标产物）。
- **E114**：即 patch 0002（umask 077 mktemp）。
- **E232**：OHOS 本机构建执行器不能直接执行源码 configure → 用
  `/system/bin/sh` 前缀驱动 configure，保留 Conan 完整参数串；
  失败时回显 config.log 尾部。
- **E074**：HMDFS jobserver fifo EPERM → `make -j1`。
- **E274**：上游 SHOBJLDFLAGS（`-shared -rdynamic`）无 -soname →
  通过 LDFLAGS 注入 `-Wl,-soname,libopennet.so.0`（configure 展开
  的 `LDFLAGS = @LDFLAGS@` 为空，需 make 命令行覆盖），保持上游
  版本化符号链接布局可用。
- **E461**：HMDFS 拒绝 AF_UNIX 文件 socket bind（EPERM），/tmp 为
  只读 erofs、/dev/shm EACCES → test_package 用 Linux abstract
  namespace socket。
- **E298**：test() 用 `self.run(..., env="conanrun")` 显式执行消费者。

## 验证结果（已实测）

- `conan create`（OHOS host+build profile）static（默认）与
  shared=True 两轮全链路通过（OHOS 本机 clang-15）。
- test_package 两种模式全部 4 项消费者测试 PASS，退出码判定，
  无 skip/timeout/fake pass：
  1. 本地文件 stdio API（覆盖 patch 0001 两个回归）；
  2. fd API（open/read_net，断言上游 lseek_net 恒 -1 的 stub 行为）；
  3. OHOS 专项：AF_UNIX abstract namespace socket（fork 服务端子进程
     + `read_net()`）；
  4. 离线网络 API：`fopen_net("http://127.0.0.1:39441/…")` 对 fork
     本地 HTTP 服务端（仅 127.0.0.1，PASS 不依赖公网）。
- readelf ELF 检查（test() 内实测）：ELF64 + AArch64；shared 消费者
  NEEDED 含 `libopennet.so.0`（by-SONAME），static 消费者不含；
  RPATH/RUNPATH 检查通过（shared by-soname 场景由 conanrun 的
  LD_LIBRARY_PATH 提供路径）。
- `python3 -m py_compile` 两个 conanfile.py 通过。

## 待办

- PR 校验流水线与远端上传未跑（单包 CI / REL upload）。
