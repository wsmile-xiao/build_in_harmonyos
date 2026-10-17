# Windows 专有 C 工具的移植模式：自包含兼容层 + 双平台 `#ifdef` + 合成 PE fixture

> 草稿（DRAFT）。与同目录 `DRAFT-ntldd-0.2-win32-pe-tool-port-compat-layer.kv` 成对。
> 以 ntldd 0.2（PE 依赖分析工具，MinGW + imagehlp 构建）为例，模式可推广到其它
> "纯文件解析、但绑死 Win32 API/头文件"的 Windows 命令行工具。

## 问题特征

上游是 Windows-only 的 C 工具，编译期硬依赖：

- `windows.h` / `winnt.h`（PE 结构定义：`IMAGE_*`、`LOADED_IMAGE` 等）
- imagehlp / psapi 等 Windows 专有库（`MapAndLoad`、`UnMapAndLoad`）
- Win32 运行时 API（`GetModuleHandleExA`、`GetLastError`、`MAX_PATH`）
- MinGW 扩展函数（`stricmp` / `strnicmp`）

但**核心逻辑是纯文件解析**（读文件、走结构、打印结果），不真正调用 Windows
运行时。鸿蒙 PC 上没有 windows.h、没有 imagehlp，看似不可移植，实则可以。

## 移植模式（四步）

1. **自包含兼容头**（新增 `pe_compat.h`）：按公开的 PE 格式规范自己定义全部
   所需结构与类型（`DWORD/WORD/BYTE/BOOL...`、`IMAGE_DOS_HEADER` 到
   `IMAGE_DELAYLOAD_DESCRIPTOR`），并在 `_WIN32` 分支里原样 include 系统头，
   保证补丁在 Windows 上仍走原生路径（双向兼容，上游不会拒）。
2. **API 替代实现**（新增 `pe_compat.c`）：把用到的每个 Win32 调用映射到等价
   POSIX 实现。关键洞察：imagehlp `MapAndLoad` 的本质就是"整文件读进内存 +
   定位 DOS/NT 头/节表"，`fopen/fread/malloc` 百行内可等价实现（含 `.dll`
   后缀 fallback 语义）。`GetLastError` 失败路径可以退化为常量。
3. **死分支隔离**：只在个别模式启用的 Win32 调用（如 ntldd 的 `on_self` 需要
   `GetModuleHandleExA`，而 CLI 从不启用）用 `#ifdef _WIN32` 包裹，非 Windows
   下直接 `return 1`，不要模拟。
4. **单命令构建**：放弃上游 MinGW 构建脚本（`makeldd.sh` 里的 `-limagehlp`），
   配方 `build()` 里一条 `cc -U_WIN32 -o <tool> a.c b.c compat.c` 完成编译；
   `-U_WIN32` 防止某些 clang 环境预定义 `_WIN32` 走错分支。

## 测试方法：合成 fixture + 独立 ground truth

被测工具吃的是 Windows PE 文件，而鸿蒙真机上没有现成 PE。做法：

- 用 Python `struct` 在 test_package 里**合成一个最小合法 PE32**（DOS 头 + PE
  头 + 一个 `.idata` 节 + 两条 import 记录，约 1.5KB），断言被测工具能列出
  预置的 DLL 依赖名与导入符号；
- 合成 fixture 的正确性**不由自己说了算**：本机先用 `llvm-objdump -p tiny.exe`
  解出同样的 import 表作为 ground truth 对照（objdump 认这个文件，工具也应认）；
- 断言里同时覆盖错误路径（列不存在的 DLL 时输出 `not found`），防止"空输出
  也算通过"的假测试（配合 CI 的 L1e 破坏性验证双保险）。

## 效果

ntldd 0.2 按此模式移植：补丁 +586 行（其中约 500 行是可复用的兼容层），上游
三个源文件改动仅 4 处 include/ifdef；OHOS 真机 shadow CI 一次通过全门禁
（L0/L1/L2/L4/L5 pass，L1e 确认真依赖，test_package 6/6 断言含真实 PE 解析）。

## 查重与边界

- 知识库现有"Windows 兼容"条目集中在 **musl/glibc 差异**（ucred、getpass、
  pthread_cancel 等），没有"整层 Win32 头 + imagehlp 替代"的移植模式条目。
- 边界：该模式只适用于**文件解析型**工具（PE/COFF/MSI/注册表 hive 解析器等）；
  真正调用 Win32 系统服务（GUI、COM、设备访问）的工具不适用，应判
  wait-for-platform-support。

## 证据

ntldd/0.2，分支 feat/ntldd-0.2-codex（commit cdc29a235d）：

- 本机 OHOS SDK clang 交叉编译通过（ELF64/AArch64）；
- 真机 shadow CI 2026-09-29 run ...-103931-45230：exit 0，L0-L5 全 pass，
  test_package 6/6（`--version`、`--help`、KERNEL32.dll/advapi32.dll 依赖列举、
  not-found 报告、`-i` 符号 Foo）。
