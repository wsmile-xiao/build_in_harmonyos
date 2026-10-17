# termrec

Record and replay terminal sessions in the ttyrec / asciicast formats —
a small tool suite plus the `libtty` terminal-recording library.

- 上游仓库: https://github.com/kilobyte/termrec
- 版本: 0.19（上游 git tag `v0.19`）
- 许可证: LGPL-3.0-only（`COPYING.LIB`）
- 类型: 库 + 命令行工具（`libtty` + `termrec` / `termplay` / `termtime` / `termcat`）
- 构建系统: autotools（tag 内不含生成的 `configure`，需 `autogen.sh` 引导）

## 用途

- `termrec`：录制终端会话为 ttyrec/asciicast 文件（支持 `.gz/.bz2/.xz/.zst` 压缩流）
- `termplay`：回放录制文件（可调速度、跳转、暂停，支持 `-p` 跟踪增长中的文件）
- `termtime`：显示录制时长/帧信息
- `termcat`：格式转换与拼接（ttyrec ⇄ asciicast）
- `libtty`：录制/回放与虚拟终端（vt100 解析、颜色、字符集、时间线）库，
  公开头文件 `libtty/tty.h`、`libtty/ttyrec.h`

## 在 OpenHarmony / HarmonyOS PC 上

- 安装内容：`bin/{termrec,termplay,termtime,termcat}`、`lib/libtty.a`（默认静态）、
  `include/libtty/{tty.h,ttyrec.h}`、`share/man/man{1,3}/*`、`licenses/COPYING.LIB`
- 消费方（CMake + Conan）：

  ```cmake
  find_package(termrec REQUIRED)
  target_link_libraries(app termrec::termrec)   # 头文件：libtty/tty.h、libtty/ttyrec.h
  ```

- **OHOS 适配要点**：上游 `termplay` 用 POSIX 线程取消（`pthread_cancel`）管理播放/加载线程，
  而 OHOS 的 musl 系 libc 不提供该 API。配方按 autoconf 能力探测（`HAVE_PTHREAD_CANCEL`）
  在无该能力时改用协作式停止（标志位 + 条件变量唤醒 + 分片 `select`），行为等价、非空壳 stub；
  glibc 平台仍走上游原生路径。详见 `3/notes.md` 与 `3/patches/`。
- 默认静态 `libtty`，工具自包含；`-o termrec/*:shared=True` 可构建动态库（运行期需
  `LD_LIBRARY_PATH` 指向包 `lib/`，OHOS musl 不识别 DT_RUNPATH）。
- 未声明 curl 依赖：`http://` 等远端源不可用（上游本身允许缺省），本地文件/管道录制回放不受影响。
