# lwtools 软件包

lwtools 是 Motorola 6809 / Hitachi 6309 处理器的开源交叉开发工具链：两遍式汇编器 `lwasm`、链接器 `lwlink`、目标文件转储器 `lwobjdump`、归档工具 `lwar`，以及实验性 C 编译器驱动 `lwcc`（含预处理组件 `lwcc-cpp` 与编译组件 `lwcc-cc`）。工具链自成体系，只产出 6809 平台的目标码/原始镜像，用于经典计算、模拟器与嵌入式 6809 开发。

上游 <https://www.lwtools.ca/>（作者 L. W. Hogg，GPL-3.0-or-later，发布目录 <https://www.lwtools.ca/releases/lwtools/>）。

## 功能概述

- `lwasm` — 6809/6309 汇编器，支持 `--raw`（原始镜像）、`--obj`（LWTOOLS 目标文件）、多段、宏与表达式求值
- `lwlink` — 链接器，把 `.obj` 归并为原始镜像/可加载镜像，支持 `-m` 映射文件输出
- `lwobjdump` — 目标文件转储/反汇编（源自 `lwlink` 代码库）
- `lwar` — 目标文件归档（create / extract / list / remove / replace）
- `lwcc` — C 编译器驱动，按 `-B<base>` 或 PATH 查找并调度 `lwcc-cpp`（预处理）与 `lwcc-cc`（编译）；上游标注为实验性、语言覆盖不完整

## 依赖关系

- 编译依赖：仅需 ISO C 编译器与 POSIX `make`/`ar`/`ranlib`，无第三方库
- 运行依赖：无第三方运行库；7 个产物均为动态链接可执行文件，设备侧 `llvm-readelf -d` 即时实测每个二进制的 `NEEDED` 只有系统 `libc.so`（该命令输出未随包存档，口径见 `4.25/notes.md` 的依赖版本小节；上游测试驱动 `test/runtests` 需要 perl，且仅用于构建期校验）

## OHOS 适配要点

- 上游为纯 POSIX Makefile（无 configure/CMake），OHOS SDK clang 直接编译通过，零平台宏注入
- 修复 1 处上游缺陷：`lwcc/cpp-main.c` 漏建全局字符串链表 `sysmacrolist`，导致 `lwcc-cpp` 处理任何输入都会在 `lw_stringlist_reset(NULL)` 处段错误（上游测试只覆盖 `lwasm`，故未暴露）；见 `4.25/patches/`
- 产物布局对齐上游 `install-all`：`bin/` 存放 7 个程序，`lib/lwcc/bin/` 存放驱动组件
- `lwcc` 驱动以 `access(X_OK)` 判定组件是否可执行，HMDFS 不上报可执行位，故配方同时导出 `PATH` 兜底（见 `4.25/notes.md`）
- 上游 272 例 opcode 回归在 OHOS aarch64 构建机全通过（272/272），无需白名单
- `lwcc` 的 C 代码生成能力本包**未作验证**：上游在 `lwcc/README.txt` 中把编译器与预处理器的"直接接口"明确定义为未定义行为，且该组件自标实验性。本包的测试只覆盖预处理链路，不声称 `lwcc` 能把 C 编译为可用目标文件

## 参考资料

- 官网与下载：<https://www.lwtools.ca/> ，发布目录 <https://www.lwtools.ca/releases/lwtools/>
- 文档（随源码发布，本包为 CLI 工具不做二次打包）：`docs/lwasm.txt`、`docs/internals.txt`、`docs/readme-4.0.txt`、`docs/manual.docbook.sgml` 与 `docs/manual/`（HTML/PDF 手册）
- 上游说明：`00README.txt`、`lwcc/README.txt`（说明 `lwcc` 为实验性、`BASEDIR` 布局）

## 版本

- `4.25` — 适配 HarmonyOS PC（aarch64-linux-ohos）；1 个上游缺陷补丁；见 [4.25/notes.md](4.25/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/lwasm` | 6809/6309 汇编器 |
| `bin/lwlink` | 链接器 |
| `bin/lwobjdump` | 目标文件转储器 |
| `bin/lwar` | 归档工具 |
| `bin/lwcc` | C 编译器驱动 |
| `bin/lwcc-cpp` | 预处理器组件 |
| `bin/lwcc-cc` | 编译器组件（上游实验性） |
| `lib/lwcc/bin/{lwcc-cpp,lwcc-cc}` | 驱动运行期组件目录（对齐上游 `install-all`） |
