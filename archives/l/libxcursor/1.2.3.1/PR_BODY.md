- **三方库名称**：libxcursor
- **上游版本**：libXcursor 1.2.3（对应 `libXcursor.so.1`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxcursor
- **适配路径**：路径 A（基础适配） + 知识库扩展（复用 X11 家族 autotools 模式）
- **使用知识库**：OHOS 下 X.Org autotools 库的通用工具链修复模式（libxkbfile/libxcb 同法）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libXcursor 1.2.3 release tarball；源码无 `TESTS`/`check_PROGRAMS` |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成库与 doxygen doc 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（61 个导出符号强类型重定位）+ `version_contract.c`（XcursorImage 等 ABI 布局 + 版本宏 + 函数签名契约），均不依赖 X server |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

libXcursor 上游只发布源码与 doxygen 文档目标，无任何自动化测试。适配后
新增两个不依赖 X server 的消费者测试：`libxcursor_api_surface` 对
libXcursor.so.1 全部 61 个导出函数（Xcursor*）强制活重定位，确保 ABI
完整；`libxcursor_version_contract` 校验 XCURSOR_LIB_VERSION=10203、
XcursorImage（7 个 CARD32 + 末尾 XcursorPixel* 指针，offsetof 断言）、
XcursorImages/XcursorFile/XcursorCursors 布局，以及 10 个导出函数通过强
类型函数指针赋值做的编译期签名契约。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，已手工核验 libXcursor-1.2.3 release tarball：无 `test/` 目录、根 `Makefile.am` 无 `check_PROGRAMS`/`TESTS`，`make check` 无可执行用例）
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`libxcursor_api_surface` + `libxcursor_version_contract` 两个 consumer 均通过）

## 补充说明

- 本 PR 只新增 `archives/l/libxcursor/1.2.3.1/` 下的 Conan 配方、元数据、test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxcursor/1.2.3`；目录使用小写 `archives/l/libxcursor/1.2.3/`，符合 conan slug 规则。
- 上游测试用例统计已通过解包 libXcursor-1.2.3 release tarball 手工核验（无 `test/` 目录、无 `check_PROGRAMS`/`TESTS`），不存在少报。

## 知识库扩展

复用 CI 实证的 libxrender/0.9.12 交叉编译模式（PkgConfigDeps+AutotoolsDeps、
build 目录私有 relocatable linker view、`--host=aarch64-linux-ohos` 交叉
configure 经 `/system/bin/sh`、.pc 相对化、移除 .la）。新增三个知识点：

1. **OHOS autoconf works-check 陷阱（关键，来自 libxrender/0.9.12 实证）**：
   OHOS worker 的 clang 无法 *运行* conftest 二进制。configure 以原生模式
   （`--build == --host`）运行时会执行 conftest 并报
   `C compiler cannot create executables`；必须以 `--host=aarch64-linux-ohos`
   （config.guess 给出 `aarch64-unknown-linux-ohos`，build≠host）进入
   cross_compiling=yes 分支，conftest 只链接不运行即通过。同一批 CI 中
   libxrender 交叉通过、libxcursor 原生失败即为实证。
2. **config.guess/config.sub 补丁（必须，来自 libxrender/0.9.12 移植）**：上游
   config.guess 不认识 HarmonyOS，fall through 到通用 Linux 分支去编译 dummy.c
   探测（需在 TMPDIR 写文件），在 OHOS worker 沙箱下报
   `config.guess[1700]: can't create .../dummy.c: Permission denied` →
   `cannot guess build type`。`0002-config.guess.patch` 在 NetBSD 分支前插入
   HarmonyOS 分支（uname -s 为 HarmonyOS 时直接 echo aarch64-unknown-linux-ohos
   退出，不再编译 dummy.c）；`0001-config.sub.patch` 把 `ohos*` 加进合法 OS
   列表、`linux-ohos*` 加进 kernel-os 校验。hunk 按 libxcursor 的
   config.guess/sub 版本（2022-01-09 / 2022-01-03）适配。
3. **依赖轨道陷阱**：制品仓 libxrender/0.9.12 的 recipe 钉 libx11/**1.8.13**，
   而 libxfixes/6.1.0 与 libxext/6.4.0 钉 libx11/**6.4.0**（cmd-pkgs 轨道，
   与已合并 libxi/libxscrnsaver 一致）。适配采用
   `self.requires("libx11/6.4.0", force=True)` 让 libxfixes/libxext 命中已
   发布二进制，libxrender/0.9.12 对 6.4.0 重新源码构建（其
   relocatable-libtool-metadata linker view 支持）。注意勿强制 1.8.13：该
   轨道 libX11.la 引用 libxcb.la 而 libxcb/1.16 不带 .la，传递依赖
   libxext/6.4.0 的源码重建会报 `is not a valid libtool archive` 失败。本 PR
   是 GUI 工具链消费 libXcursor（光标主题）的构建前置。
