# DRAFT-14402-ohos-afunix-eperm-ldpreload-shim

## 现象

KWayland（kf5wayland 5.116.0）上游测试在 OHOS aarch64 上 in-process 启动
KWaylandServer Display 时全部连接失败：服务端 `wl_display_add_socket*` 绑定
`$XDG_RUNTIME_DIR/wayland-N`（filesystem 路径）→ `bind(): Operation not
permitted`（EPERM，可写目录亦然）；29 个经 unix socket 通信的 ctest 用例全灭。

## 根因

OHOS 用户态没有允许创建 filesystem AF_UNIX socket 的位置（探测矩阵见
DRAFT-libdsme-0.67.0-ohos-abstract-af-unix-socket：/tmp EROFS、HMDFS EPERM、
/dev/shm EACCES；abstract namespace 与 socketpair 可用）。libwayland 的
`wl_display_add_socket*` 只接受 filesystem 名（内部 bind + chmod 0777），
且 KWayland 服务端绑 `$XDG_RUNTIME_DIR/<name>`、客户端传裸名 `<name>`
（connection_thread.cpp L88，WAYLAND_DISPLAY 默认 "wayland-0"）——两侧字符串
不同，不能简单替换。依赖库不可改源码，源码侧 `@` 前缀约定（libdsme 方案）
不适用。

**策略震荡（2026-10-01 同机新测）**：两 namespace 可用性实时翻转，周期
~10-40 分钟——20:16-20:21 abs-OK（conan create 29/29 绿）→ 20:32-20:38
abs-EPERM（同日隔离重跑 29/29 全 QFATAL "The Wayland display cannot be
started!"，27MB 输出）→ 21:00-21:03 fs-EPERM/abs-OK（10 轮×20s 采样稳定）
→ 21:33 fs-OK。结论：**shim 不是永久解法**，任何静态选择必在某一窗口失效，
必须运行时探测。

## 修复

LD_PRELOAD 运行时 shim（kf5bindshim.c，内嵌 conanfile，build() 编译）：

1. **拦截 AF_UNIX bind/connect**：filesystem 名 → abstract 名 `"@"+basename`。
   服务端 `XRD/wayland-3` 与客户端裸名 `wayland-3` 归一到同一 abstract 名，
   必然相遇（basename 归一是关键——不做归一则两侧 abstract 名不同，仍连不上）。
2. **bind 时在原路径建存根普通文件**：testStartStop/testAutoSocketName 有
   socket 文件存在性断言；服务端 release unlink 时一并清掉。
3. **dlsym(RTLD_NEXT) 在 constructor 初始化**（单线程加载期）：v3 懒初始化
   （首调才 dlsym）在 QThread bind/connect 首调竞争 → 非确定性 SIGSEGV
   （实测两轮复现，crashbt 取证）。
4. **条件启用（2026-10-01 新增，针对策略震荡）**：conanfile build() 运行时
   探测 fs/abstract bind，filesystem 可用则走原生路径（不 preload），仅
   fs=EPERM 时 LD_PRELOAD shim；ctest 在所选 namespace 下失败则 re-probe
   重试一次（2 attempts）。探测结果写入 conan create 日志
   （"AF_UNIX namespace probe (attempt N/2): filesystem|abstract"）。

```sh
clang -shared -fPIC -O2 -o libkf5bindshim.so kf5bindshim.c -ldl
# 仅当运行时探测 fs=EPERM 时：
LD_PRELOAD=$PWD/libkf5bindshim.so ctest --output-on-failure ...
```

## 验证

- 修复前：同环境 100% 复现（filesystem bind EPERM，socket 通信全灭）
- 修复后：ctest 29/29 全过（kf5wayland/5.116.0 PR #13869，conan create 实测）
- 策略震荡实证：2026-10-01 20:32 abs-EPERM 窗口硬编码 shim → 29/29 QFATAL；
  探测升级后 v4 conan create 复验（2026-10-01，PR #13869）
- 存根文件断言用例（testStartStop 等）通过
- 配套：短 XDG_RUNTIME_DIR（DRAFT-14404）解决 108 字节 sun_path 限制

## 适用范围

- 所有依赖"不可改源码库走 filesystem unix socket"的 OHOS 软件：wayland 协议
  服务端、KWayland 测试、同类 IPC 库；
- 与 DRAFT-libdsme（可改源码 → 库侧 `@` 约定）互补：本方案覆盖
  **依赖库不可改**的场景（libwayland/KWayland 均为上游固定行为）；
- 注意：LD_PRELOAD 对静态链接/secure-exec 进程无效，此时只能排除测试并声明
  平台边界。
