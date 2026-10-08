# DRAFT-hmdfs-odirect-existing-file-open-einval

## 使用说明

任何上游源码含 `open(..., O_DIRECT ...)` 的 C/C++ 包，在 HarmonyOS PC 真机上
以"传 EINVAL → 按上游既有可移植分支回退"的固定模式适配。本条给出：
① 判定特征（一条命令区分"文件系统不支持"与"代码缺陷"）；② 最小回退补丁
模板；③ 不适用时的处置路径。

## 适用范围

- 触发：包在真机运行时报 `open: Invalid argument`（errno 22, EINVAL），
  编译期无任何问题（musl 定义 O_DIRECT，`#error "Needs O_DIRECT"` 类守卫
  可通过）。
- 适用：数据面用普通文件做 O_DIRECT IO 的基准/工具类程序。HMDFS 的行为
  是**非对称**的——`open(path, O_CREAT|O_RDWR|O_DIRECT)` 创建新文件成功，
  对**已存在**文件 `open(path, O_RDWR|O_DIRECT)` 返回 EINVAL。这会误导
  仅用"创建探测"得出的结论。
- 依据：randomio 1.4 真机 r2（2026-10-03），两个独立复现（python os.open
  探测 + 直接运行二进制），error_signature 稳定。

## 输入输出定义

- 输入：真机 SSH 会话；待探测目录（默认 `$HOME`）；包内 O_DIRECT 打开点
  的源码位置。
- 探测输出：每个候选目录一行 `O_DIRECT OK|FAIL: <dir> <errno描述>`。
  - `/data/local/tmp` → EACCES（shell 用户无权限，与 O_DIRECT 无关）
  - `/tmp` → EROFS（只读，与 O_DIRECT 无关）
  - `$HOME`（HMDFS）→ 新文件 OK / 已存在文件 **EINVAL**
- 修复输出：EINVAL 时回退缓冲 IO 并向 stderr 打一行 warning；延迟语义
  变化（含页缓存）必须在 notes/manifest 声明。

## 示例

探测（设备端 python3，经 base64 传入，勿用 heredoc——/tmp 只读）：

```python
import os
OD = 0x4000  # O_DIRECT on aarch64 linux
p = os.path.join(d, "od_probe")
fd = os.open(p, os.O_CREAT | os.O_RDWR | OD)      # 新文件：OK
os.close(fd)
fd = os.open(p, os.O_RDWR | OD)                    # 已存在文件：EINVAL (HMDFS)
```

最小回退补丁模板（镜像上游自身的 `__APPLE__ OPEN_FLAGS=0` 分支，用
`#ifdef O_DIRECT` 预处理守卫避免 -Wconstant-logical-operand 警告）：

```c
globals.fd = open(filename, OPEN_FLAGS | (write ? O_RDWR : O_RDONLY));
#ifdef O_DIRECT
if (globals.fd == -1 && errno == EINVAL) {
    fprintf(stderr, "warning: O_DIRECT unsupported on %s, falling back to buffered I/O\n", filename);
    globals.fd = open(filename, write ? O_RDWR : O_RDONLY);
}
#endif
```

配方侧：补丁经 `exports_sources = "patches/*"` 导出、
`conan.tools.files.patch()` 应用（见 DRAFT-conan2-patch-tool-keyword-call）。

## 不适用 / 反例

- 对**块设备/裸盘**（/dev/block/...）做真直 IO 的场景不适用本回退——那是
  有效直 IO 路径，EINVAL 应如实报错而非掩盖。
- 回退后测试若声称"直 IO 基准通过"属于语义失真：必须像 randomio 一样把
  "O_DIRECT 不受支持、延迟含页缓存"写进 manifest/notes，测试断言只针对
  功能性（表格结构/退出码），不断言直 IO 数值。
- ext4/f2fs 数据分区不受此影响；不要因 HMDFS 行为推断整个平台无 O_DIRECT。
