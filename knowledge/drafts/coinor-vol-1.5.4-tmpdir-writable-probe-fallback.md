# 配方设置 TMPDIR 时须真实写入探测并回退 build_folder

> DRAFT-coinor-vol-1.5.4-tmpdir-writable-probe-fallback（知识库扩展草稿，路径 B）
> 与 coinor-vol 1.5.4 归档同 PR 交付（PR #8922 本轮更新批次）。

## 问题

HarmonyOS 设备 `/tmp` 为 erofs 只读（E002），autotools 工程在设备本地构建时需
`TMPDIR=$HOME/tmp` 规避。但把该方案直接写进 conan 配方（`build()` 无条件
`os.environ["TMPDIR"] = $HOME/tmp"`）后，**远端 CI worker 上 configure 的首个
C 编译器测试失败**：

```text
checking for C compiler default output file name... configure: error: C compiler cannot create executables
```

conan `build()` 返回 Error 77。CI 日志不含 config.log，首个真实错误被 configure
汇总行掩盖。`curl` 缺失、源码下载、补丁应用均与此无关——官方归档下载、解压、
5 个补丁全部成功后才在首个编译测试失败。

## 根因

- 配方把 `TMPDIR` 硬编码为 `$HOME/tmp`（E002 建议的 HMDFS 规避）
- CI worker 沙箱下 `$HOME/tmp` **不存在**（`No such file or directory`）或
  **对构建用户不可写**（`Read-only file system` / `Permission denied`）
- clang 依赖 `TMPDIR` 创建编译临时文件；失败 → configure 首个 C 编译测试
  `C compiler cannot create executables` → Error 77
- 编译器本身可用（`clang --version` rc=0），与工具链/sysroot/链接器无关

## 等价复现（同一官方 tarball sha256=93c2afff...，同一 configure 命令）

| TMPDIR | 结果 | config.log 首错 |
|--------|------|-----------------|
| 可写目录 `$HOME/tmp` | 通过 | — |
| 只读 `/tmp`（erofs） | **Error 77** | `clang-15: error: unable to make temporary file: Read-only file system` |
| 不存在的目录 | **Error 77** | `clang-15: error: unable to make temporary file: No such file or directory` |

复现日志 SHA-256（config.log）：`d279d58bdabc3456ba5dfe31a39fa248abcc2428b5e688986f97c9a51519e10a`
（只读）、`f72d1e1b233f0206e92bd39f02148957cfb45a90f71cc2a75cee2ce8623de368`（不存在）。

## 方案（最小修复）

`build()` 中从候选列表挑选 TMPDIR，**用真实文件写入探测**（HMDFS 忽略 chmod、
`os.access(X_OK)` 恒 False，见 E046/R49，必须 `makedirs + open(w) + unlink` 实测）：

1. 候选一：`$HOME/tmp`（E002 原方案）
2. 候选二：conan `build_folder/.tmp`（conan 已在该目录落盘源码与补丁，可写性
   由构建工具链保证，CI worker 亦成立）
3. 全部不可写才退回 `$HOME/tmp`（至少可给出明确失败而非静默）

```python
# conanfile.py build() 片段
_tmpdir = None
for cand in (os.path.join(os.environ.get("HOME", "/tmp"), "tmp"),
             os.path.join(self.build_folder, ".tmp")):
    try:
        os.makedirs(cand, exist_ok=True)
        probe = os.path.join(cand, ".tmp-write-probe")
        with open(probe, "w") as _pf:
            _pf.write("ok")
        os.unlink(probe)
        _tmpdir = cand
        break
    except OSError:
        continue
if _tmpdir is None:
    _tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
os.environ["TMPDIR"] = _tmpdir
os.environ["TMP"] = _tmpdir
```

## 验证

- 只读/不存在 TMPDIR 下同一 configure 命令复现 Error 77 与 CI 完全一致
- 修复后本地全量 conan create：`a.out` / `C compiler works... yes` /
  `Package created` / test_package 1/1 Passed（rc=0）
- 回退探测单测：HOME=/tmp（erofs 只读）→ `$HOME/tmp` 探测失败 → 正确回退
  `build_folder/.tmp`（rc=0）

## 适用边界与反例

- 适用：autotools/library 配方需在 HMDFS/CI worker 上设置 TMPDIR 的场景
- 反例：纯 CMake 且使用 conan 默认临时目录的工程不涉及；系统级 `/usr` 注入
  （R49/PF6 禁止）与本问题无关
- 边界：若配方不设置 TMPDIR 而依赖工具默认值，设备本地/CI 均会在 `/tmp` 处失败
  （回到 E002）；本方案补齐的是"E002 建议目标本身不可写"的缺口

## 关系

- similar_to: E002（/tmp 只读 → TMPDIR 直设）、E046（HMDFS 忽略 chmod/os.access）
- caused_by: E002 场景扩展（建议目标目录本身不可用）
- 查重决定：`new_draft`（E002 部分覆盖 + boundary_novelty=yes）