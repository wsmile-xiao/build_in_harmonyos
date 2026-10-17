# DRAFT — h3 4.4.1：musl/OHOS libc 上 sscanf 带宽度 `%c` 短输入返回 0，CLI 参数解析失败

> 状态: 草稿（基于 h3 4.4.1 R01 本地全量 ctest 真实证据，查重未命中 → 路径 B 候选）。
> 触发: h3 4.4.1 R01（pc1-45，2026-09-06，task h3-4.4.1-r01-bootstrap-and-adapt-pc1-45-20260906T140731Z）。
> 查重: 正式知识 E004/E013/E014/E019/E020/E026/E029/E032/E033/E039/E055/E063/E078/E081/E085/E086/E088 均属 musl/glibc 其他差异面（dlopen/TLS/iconv/posix_spawn/-Werror 等），无任何条目覆盖「sscanf 带宽度 %c 在 musl 上短输入返回 0」；草稿 DRAFT-*（jwt-cpp/ring-span-lite 等）覆盖 conandata 注释 URL 与基线噪声主题，非本主题。查重未命中。

## 真实问题（场景）

h3 4.4.1（Uber H3 六边形地理索引库）CLI 应用（`src/apps/filters/h3.c`、`src/apps/applib/include/args.h`）用
`sscanf` 的**带宽度 `%c`** 转换扫描字符串参数：

```c
Arg filenameArg = { .names = {"-i", "--file"}, .scanFormat = "%1023c", ... };
Arg polygonStrArg = { .names = {"-p", "--polygon"}, .scanFormat = "%1500c", ... };
Arg cellStrsArg = { .names = {"-c", "--cells"}, .scanFormat = "%1500c", ... };
```

本环境 libc（musl 系，与 OHOS 同源）下，`sscanf(input, "%1023c", buf)` 在**输入短于宽度**时
转换失败返回 0（glibc 返回 1、读到可用字符为止）。`_parseArgsList` 随即输出
`Failed to parse argument: -i/-p/-c` 并打印 help，CLI 多边形/cells 命令全部不可用。

## 证据

- 全量 ctest：修复前 **311 个用例失败 73 个**（全部为 CLI 多边形/cells/KML 参数类：testCliMaxPolygonToCellsSize*、
  testCliPolygonToCells*、testCliUncompactCells* 等），单元测试全过（238 过）。
- 最小复现（python3 ctypes 调 libc sscanf）：
  - `sscanf("/path/polygon_test1.txt", "%1023c", buf)` → **0**（musl；glibc 返回 1）
  - `sscanf(same, "%1023[^\n]", buf)` → **1**（扫描集短输入成功）
  - 含换行的 JSON cells 数组（`[\n "..."...]`）：`%1500c` → 0；`%1500[^~]` → 1（`[^\n]` 会在首个换行截断，不适合多行输入）
- 修复后全量 ctest：**311/311 通过（100%）**。

## 根因

musl libc 的 `sscanf` 对带宽度 `%c` 转换要求匹配满宽度字符数；输入不足时该转换失败（返回 0）。
glibc 语义为「最多读宽度个字符，可部分成功」。这是两类 libc 的 `%c` 语义差异，非 h3 库逻辑缺陷。
`parseArgs` 把 sscanf 返回 0 当作解析失败（`PARSE_ARGS_FAILED_PARSE`），导致 CLI 不可用。

## 修复方案

将 CLI 参数的 `scanFormat` 从 width-`%c` 替换为等价**扫描集**（glibc/musl 语义一致、短输入均成功）：

| 原格式 | 新格式 | 适用 |
|---|---|---|
| `%1023c` | `%1023[^\n]` | 单行值：文件名、多边形字符串 |
| `%1500c` | `%1500[^\n]` | 单行值：多边形字符串 |
| `%1500c` | `%1500[^~]` | 含换行的多行输入（JSON cells 数组） |
| `%255c` | `%255[^\n]` | KML name/desc 单行值 |

注意：含换行的多值输入不能用 `[^\n]`（在首个换行处截断），应选输入中不会出现的哨兵字符
（如 `~`）作扫描集排除项。修改文件：`src/apps/filters/h3.c`（17 处）、`src/apps/applib/include/args.h`（2 处），
随配方归档为 patches/0001-args.h、0002-h3.c。

## 验证方法

```bash
# 修复后全量复跑
cd <build> && ctest --output-on-failure   # 311/311 通过
# 最小实证（任一 libc 上）
python3 - <<'EOF'
import ctypes
libc = ctypes.CDLL("libc.so.6"); libc.sscanf.restype = ctypes.c_int
b = ctypes.create_string_buffer(2048)
print(libc.sscanf(b"short", b"%1023c", b), libc.sscanf(b"short", b"%1023[^\\n]", b))
EOF
```

## 适用边界

- 适用于所有在 C/C++ CLI 参数解析中用 `sscanf` 带宽度 `%c` 扫描字符串、且目标为 musl/OHOS
  （或任何与 glibc `%c` 语义不同的 libc）的项目；跨库可复用（任何此类 CLI 都会命中）。
- 不适用于：纯 glibc 目标（无差异）；输入恒等于满宽度（无差异）；`%s`/`%[` 之外的其他转换。

## 反例 / 限制

- 直接用 `%[^\n]` 处理含换行输入是**反例**（首个换行截断 → 解析到不完整值）。
- 扫描集 `%[...]` 若输入以排除字符开头会匹配失败返回 0——哨兵字符必须确保输入中不出现。
- 本条目只覆盖 libc `%c` 语义差异本身；h3 具体参数表改动见 patches/，不在此重复。

## 关联

- 知识路径 B（new_draft）：无等价命中且可跨库复用。
- 同任务等价命中（走路径 A，不新建草稿）：conandata 注释裸 URL 被 pre-download 误提取子串改写
  → DRAFT-jwt-cpp-0.7.1-conandata-comment-url-predl / DRAFT-ring-span-lite-0.7.0-conandata-comment-url-predl-pollution；
  W3 JC5 全仓扫描基线噪声隔离 → DRAFT-libfort-0.4.2 / DRAFT-libpopcnt-2.0-w3-baseline-junk-check-full-scan。
