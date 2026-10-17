# wev 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure/cmake/meson）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，target aarch64-linux-ohos）
- 状态: published（conan create + test_package 全绿，本地 W3 验证通过）

## 编译步骤

上游 Makefile 把「取参数」全部交给 pkg-config，配方不改源码，只在 generate()
里准备一个可用的工具/元数据环境：

1. 逐依赖扫描 `<pkg>/lib/pkgconfig`、`<pkg>/share/pkgconfig`，把每个 `.pc` 复制到
   私有 `fixed_pkgconfig/` 并把 `prefix/exec_prefix/libdir/includedir` 重写为真实包
   目录（制品仓里的 `.pc` 带有 `/` 或旧构建缓存 `…/p/b/<hash>/p` 前缀），该目录置于
   `PKG_CONFIG_PATH` 首位。
2. 复制 wayland 包的 `bin/wayland-scanner` 到私有 `scanner/` 并**签名**（见问题 1），
   再合成 `wayland-scanner.pc`（暴露 `wayland_scanner` 变量）覆盖上游 `.pc`。
3. 合成 `scdoc.pc`（上游 scdoc 不装 `.pc`，而 Makefile 要 `pkg-config --variable=scdoc scdoc`）。
4. 在 `pkgconfig_bin/` 建 `pkg-config` → `pkgconf` 的 shim（pkgconf 只装 `bin/pkgconf`）。
5. `PATH` 前置各依赖 `bin`、`LD_LIBRARY_PATH` 前置各依赖 `lib`（普通 soname 由此解析）。
6. build: `make CC=<clang from conf> -j1`，在 `source_folder` 内执行（协议源文件就地生成）。

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
```

Makefile 实际编译命令（配方未介入）：
```bash
cc -std=c11 -o wev wev.c shm.c xdg-shell-protocol.c wayland-tablet-protocol.c \
   $(pkg-config --cflags --libs wayland-client xkbcommon) -lrt
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `wayland-scanner` 执行报 `Operation not permitted`（rc=126），chmod 无效 | 制品仓 wayland 包的 scanner 未带 `.codesign`，HMDFS 上内核拒绝执行未签名 ELF（E077） | 复制到私有 `scanner/` 后用 `binary-sign-tool` 签名（`add codesign section success`），再合成 `.pc` 指向该副本；与 grim 1.4.0 的处理一致 |
| 2 | 签名后报 `Error loading shared library /…/.cache/conan2/p/expat<hash>/p/lib/libexpat.so` | 发布机把依赖以**绝对路径**写进 scanner 的 `DT_NEEDED`（`patchelf --print-needed` 已证实），本机 `CONAN_HOME=~/.conan2` 时该路径不存在 | 让 conan 缓存同时在该路径可见（`~/.cache/conan2` → `~/.conan2`）；CI/release worker 本身即 `~/.cache/conan2` 布局，故 CI 侧无需额外处理 |
| 3 | `Error loading shared library libxml2.so.16`（签名后、且仅剩此项） | `libxml2.so.16` 是普通 soname，不在默认搜索路径 | 配方 `generate()` 已把所有依赖 `lib` 目录前置到 `LD_LIBRARY_PATH`，该错误即消失 |
| 4 | `pkg-config` 取到的 `.pc` 前缀为 `/` 或 `…/p/b/<hash>/p` | 制品仓 `.pc` 由发布机生成，前缀是其构建缓存路径 | 私有 `fixed_pkgconfig/` 重写前缀（hyprpicker/wayland 先例） |
| 5 | `pkg-config --variable=scdoc scdoc` 为空 → 无法生成 `wev.1` | scdoc 上游不安装 `.pc` | 配方合成 `scdoc.pc`（暴露 `scdoc` 变量），不改上游源码 |
| 6 | Makefile 调用 `pkg-config`，但 pkgconf 包只提供 `bin/pkgconf` | 包名与工具名不一致 | 构建目录内建同名 shim 并前置 PATH（不注入 `/usr/local`，R49） |
| 7 | `make` 在 build 目录找不到 Makefile | `basic_layout()` 分离了 source/build 目录 | `self.run("make …", cwd=self.source_folder)`（scdoc 配方同惯例） |

### 已排除的方案（负结果，勿重复尝试）

`patchelf --replace-needed` 改写 scanner 的绝对 `DT_NEEDED`：

- 先 patchelf 再签名 → `binary-sign-tool` 报 `WriteCodeSignBlock error`，产物无签名，执行仍 EPERM；
- 先签名再 patchelf → `patchelf: open: Operation not permitted`（签名后的文件不可再写）。

结论：该绝对路径问题不能靠改写 ELF 解决，只能在环境布局/IPC 依赖链层面消除。

## 源码修改

无补丁：`patches/` 为空。平台差异全部通过配方侧的私有目录（`.pc`/shim/签名副本）解决，
上游 `wev.c`、`shm.c`、`Makefile` 未改动一行。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| wayland | 1.24.0 | `wayland-client` 库 + `wayland-scanner` 代码生成器 |
| libxkbcommon | 1.13.1 | 键位/键名解析（`xkbcommon.pc`） |
| libffi | 3.4.4 | `wayland-client.pc` 的 `Requires.private` |
| wayland-protocols | 1.47 | `xdg-shell` / `wayland-tablet` 协议 XML（`pkgdatadir`） |
| scdoc | 1.11.0 | 生成 `wev.1` man page |
| pkgconf | 3.0.6 | `pkg-config` 实现 |
| expat | 2.8.2 | wayland-scanner 运行时依赖（传递） |
| libxml2 | 2.15.3 | wayland-scanner 运行时依赖（传递） |

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# wev/1.1.0: Created package ...
# test_package:
#   PASS: wev -h 打印 usage 并以 0 退出
#   PASS: wev 无显示服务器时按预期报错退出（rc=1）
#   PASS: readelf 确认 wev 链接 libwayland-client 与 libxkbcommon
#   all wev test_package assertions passed
```

上游测试清点（R51）：wev 上游仓库**不含测试套件**（无 `tests/` 目录，Makefile 只有
`all/install/clean` 目标），故 test_package 采用「运行真实二进制 + 检查依赖链」的消费
验证：`wev -h` usage 路径、无显示服务器时的 `wl_display_connect` 失败路径（证明运行时
真的加载了 wayland-client / libxkbcommon）、`readelf -d` 动态依赖检查。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/wev` | Wayland 事件查看器（aarch64-linux-ohos 可执行） |
| `share/man/man1/wev.1` | man page（由 scdoc 从 `wev.1.scd` 生成） |
| `commands.json` | 软件级命令声明（R38，`wev` 为 CLI 工具） |

## 注意事项

- wayland-scanner 需要签名才能在本平台执行；配方已内置该步骤（签名工具缺失的宿主上
  自动跳过，交由宿主环境处理）。
- wev 运行需要可用的 Wayland 合成器；无合成器时按上游逻辑退出 1 并打印
  `Failed to connect to Wayland display`。
- 制品仓 `.pc` 前缀不可信是通用现象（发布机路径），后续 Wayland 系软件可直接复用本
  配方的「私有 fixed_pkgconfig + 合成 .pc」模式。

## 对话记录

### 对话 #1 — 适配路径确认（2026-09-25）

- **任务**：把 wev 1.1.0 适配到 HarmonyOS PC（arm64），按 openharmony-compile-agent
  的 W0→W5 流程产出可合入的配方。
- **关键判断**：wev 是 Wayland 客户端 CLI，与先例 grim / hyprpicker 同族（Makefile /
  meson + pkg-config），复用其「私有 .pc 前缀重写」模式；构建系统由 init-build 误判为
  autotools，实测上游只有手写 Makefile，故按 makefile 编写配方并在 manifest 中订正。

### 对话 #2 — scanner 不可执行与绝对路径（2026-09-25）

- **现象**：`make` 生成协议代码时 `wayland-scanner` 报 `Operation not permitted`（rc=126）；
  用 `binary-sign-tool` 签名后可执行，但又报 `Error loading shared library …/libexpat.so`。
- **取证**：`patchelf --print-needed` 显示制品仓 scanner 的 `DT_NEEDED` 里烘的是发布机
  绝对路径（`/…/.cache/conan2/p/expat<hash>/p/lib/libexpat.so`）；本机 `CONAN_HOME` 为
  `~/.conan2`，故路径不存在。让 conan 缓存同时出现在该路径后恢复正常。
- **被否决的方案**：`patchelf --replace-needed` 改写 NEEDED——先改后签报
  `WriteCodeSignBlock error`，先签后改报 `open: Operation not permitted`，故配方不采用
  任何 ELF 改写，改为「签名私有副本 + 环境布局对齐」。

### 对话 #3 — 验证口径（2026-09-25）

- **W3**：`conan create --build=missing`（与 CI 同口径，不含任何本机专用参数）编译 +
  test_package 三条断言全过；`.ci-result.json` 记录 `exit_code=0` 与日志 SHA256。
- **未做的事**：未改动上游源码、未新增补丁、未使用 `--build` 强制源码重建依赖
  （wayland 等走制品仓预编译二进制）。

---

**编译结束**: 2026-09-25 17:52
**最终状态**: published
