- **三方库名称**：libxkbfile
- **上游版本**：libxkbfile 1.1.3（对应 `libxkbfile.so.1.0.2`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxkbfile
- **适配路径**：路径 A（基础适配） + 知识库扩展（draft 知识解决一类问题）
- **使用知识库**：OHOS 下 X.Org autotools 库的通用工具链修复模式

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libxkbfile 1.1.3 release tarball；源码无 `check_PROGRAMS`/`TESTS` |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成库和文档/spec 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（54 个导出符号强类型重定位）+ `version_contract.c`（XkbFileInfo ABI 布局 / 文本格式函数签名契约），均不依赖 X server |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

libxkbfile 上游只发布源码与文档目标，无任何自动化测试。适配后新增两个
不依赖 X server 的消费者测试：`libxkbfile_api_surface` 对
libxkbfile.so.1 全部 54 个导出函数（Xkb*/Xkm*，排除 `#define` 宏与内部
符号）强制活重定位，确保 ABI 完整；`libxkbfile_version_contract` 校验
XkbFileInfo ABI 布局（type/defined 两个 unsigned + 末尾 XkbDescPtr 指针，
64 位下 16 字节）、文件类型常量（XkbXKMFile..XkbMessage）与
XkbKeysymText/XkbKeyNameText/XkbAtomText 的强类型函数指针签名契约。

## 知识库扩展

新增 draft 知识 **E342：X11 库头文件自包含陷阱**（`knowledge/drafts/E342-*`）。
libxkbfile 的 `XKBfile.h` 不含任何 `#include`，却使用 `FILE *`/`XkbDescPtr`/
`Bool`/`KeySym` 等外部类型，且 `#define` 宏（XkbMapDefined、XkbKSIsLower 等）
与真函数混排。适配记录了两条可复用经验：消费者需按序补齐 stdio.h →
Xlib.h → XKBstr.h 再引库头；生成 api_surface 符号面时必须先排除宏表再以
`src/*.c` 定义做二次核对，否则 `undefined reference` 误判库缺符号。该模式
可直接复用于 Xcursor/Xrandr/Xft 等其余 X11 家族库。

另补充两个构建期知识点（复用 E342 已验证的 X11 autotools 模式）：

1. **OHOS autoconf works-check 陷阱**：本机模式（`--build == --host`）下
   works-check 会*执行* conftest，被 OHOS 沙箱拦截（`C compiler cannot
   create executables`，worker 相关、非确定）。改为
   `--host=aarch64-linux-ohos`（build ≠ host）进入交叉模式后仅链接即通过。
2. **config.guess/config.sub 补丁**：libxkbfile 的 config.guess/config.sub
   版本（2023-01-01 / 2023-01-21）与 libxpm 3.5.17 完全一致，直接复用
   libxpm 的两个 conandata 补丁（合法 OS 加 `ohos*`、kernel-os 加
   `linux-ohos*`；config.guess 在 NetBSD 分支前插入 HarmonyOS 分支）。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，已手工核验 libxkbfile-1.1.3 release tarball：无 `test/` 目录、根 `Makefile.am` 无 `check_PROGRAMS`/`TESTS`，`make check` 无可执行用例）
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`libxkbfile_api_surface` + `libxkbfile_version_contract` 两个 consumer 均通过）

## 补充说明

- 本 PR 只新增 `archives/l/libxkbfile/1.1.3/` 下的 Conan 配方、元数据、test_package 与 `knowledge/drafts/E342-*` 知识草稿，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxkbfile/1.1.3`；目录使用小写 `archives/l/libxkbfile/1.1.3/`，符合 conan slug 规则。
- 上游测试用例统计已通过解包 libxkbfile-1.1.3 release tarball 手工核验（无 `test/` 目录、无 `check_PROGRAMS`/`TESTS`），不存在少报。
