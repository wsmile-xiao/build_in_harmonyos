# E332: Autotools 三方库 CI 构建失败——共享 SYS_PREFIX 注入污染 + 真实缺失依赖清单

> **结构化数据**: [draft/E332-draft-2301-asterisk-srtp-private-prefix.kv](../draft/E332-draft-2301-asterisk-srtp-private-prefix.kv)
> **严重度**: 🔴 blocking | **分类**: conan / dependency / build / CI / autotools | **自动修复**: ❌ manual
> **来源**: asterisk-srtp 22.10.1 PR #6055（19 轮 CI 全部失败，方案 C 后首次真正 PASSED）

---

## 错误特征

```
checking for aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang
checking whether the C compiler works... no
configure: error: in '.../menuselect':
configure: error: C compiler cannot create executables
```

或（补依赖后继续暴露）：

```
checking for uuid_generate_random in -luuid... no
configure: error: *** uuid support not found (this typically means the uuid development package is missing)
```

```
checking for jansson >= 2.11... no
configure: *** Asterisk requires libjansson >= 2.11 and no system copy was found.
```

```
checking for sqlite3_open in -lsqlite3... no
configure: error: *** Asterisk now uses SQLite3 for the internal Asterisk database.
```

## 根因（两个叠加）

### 根因 1：依赖注入污染共享 SYS_PREFIX（C compiler cannot create executables 的真正元凶）

CI worker 与本地**共享同一台机器的文件系统**（buildbot worker 在
`/storage/Users/currentUser/.cache/buildbot-worker`，HOME 相同，SYS_PREFIX
`/storage/Users/currentUser/usr/local` 是共享目录）。

配方 `generate()` 此前把 libedit/libxml2/ncurses 注入到共享 SYS_PREFIX。CI 从
制品仓下载的依赖包 revision 与本地不同（共享库版 vs 静态库版、.pc 布局不同），
注入后**污染共享目录** → clang 链接 conftest 时 `-L/usr/local/lib` 找到坏库 →
`C compiler cannot create executables`。

**关键特征**：本地永远无法复现（本地共享目录恰好是好的/有历史遗留），
19 轮 CI 全部失败、换 worker/换 work 目录/加 ac_cv 均无效。

### 根因 2：Asterisk configure 逐项硬性 REQUIRED 依赖缺失

改私有 prefix 后真实暴露（此前共享目录有历史遗留所以本地能过）：
libedit、uuid(e2fsprogs)、jansson(>=2.11)、sqlite3、libxml2(menuselect)、ncurses(tinfo)。

### 根因 3（辅助陷阱）：HMDFS 上 os.access(X_OK) 恒为 False

HMDFS chmod 被忽略、权限固定 660 → `os.access(path, os.X_OK)` 永远 False →
用其探测 work 目录可执行性会永远回退到 CI 上 noexec 的 `$TMPDIR` 派生路径 →
conftest 无法生成 → C compiler cannot create executables。

## 受影响范围

- 所有基于 autoconf 的三方库适配（Asterisk 系列及后续同类库）
- 所有 `generate()` 向共享 SYS_PREFIX 注入依赖的配方
- CI worker 与本地共享文件系统的场景

## 解决方案（推荐：方案 C——私有 prefix 注入）

### 1. 依赖注入目标改为 build_folder 私有 prefix

```python
def _prefix(self):
    """依赖注入目标 = build_folder 私有目录（不污染共享 /usr/local）。"""
    return os.path.join(self.build_folder, "prefix")
```

`generate()` 中所有 `_ensure_*(SYS_PREFIX, pkg)` 改为 `_ensure_*(self._prefix(), pkg)`；
CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH 同步指向私有 prefix。

### 2. 按 configure 报错逐项补齐 REQUIRED 依赖

| 依赖 | 提供包（ohpcd） | 备注 |
|------|----------------|------|
| libedit | libedit/20240808 | REQUIRED（硬错误） |
| libxml2 | libxml2/2.15.3 | menuselect 子 configure REQUIRED |
| ncurses | ncurses/6.6 | libedit.pc Libs.private=-ltinfo |
| uuid | e2fsprogs/1.47.4 | REQUIRED uuid_generate_random |
| jansson | jansson/2.15.1.1 | REQUIRED >=2.11；只发布共享库（libjansson.so 无 .a） |
| sqlite3 | sqlite3/3.49.1 | REQUIRED；包无 .pc → 生成 shim |

sqlite3.pc shim 示例：

```python
def _ensure_sqlite3_pc(prefix):
    pc_dir = os.path.join(prefix, "lib", "pkgconfig")
    os.makedirs(pc_dir, exist_ok=True)
    pc = os.path.join(pc_dir, "sqlite3.pc")
    if not os.path.exists(pc):
        with open(pc, "w", encoding="utf-8") as f:
            f.write("prefix=%s\n" % prefix)
            f.write("exec_prefix=${prefix}\nlibdir=${exec_prefix}/lib\n"
                    "includedir=${prefix}/include\nName: SQLite\n"
                    "Description: SQLite3 shim\nVersion: 3.49.1\n"
                    "Libs: -L${libdir} -lsqlite3\nCflags: -I${includedir}\n")
```

### 3. work 目录直接用 build_folder 子目录（禁止 os.access 探测）

```python
work = os.path.join(self.build_folder, "worktree")
if os.path.exists(work):
    shutil.rmtree(work)
os.makedirs(os.path.dirname(work), exist_ok=True)
shutil.copytree(self.source_folder, work, ignore=shutil.ignore_patterns(".tmp"))
```

## 验证命令

```bash
conan create archives/a/asterisk-srtp/22.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# 期望日志：
#   checking whether the C compiler works... yes
#   checking for uuid_generate_random in -luuid... yes
#   checking for jansson >= 2.11... yes
#   checking for sqlite3_open in -lsqlite3... yes
#   config.status: creating makeopts
#   [LD] res_srtp.o -> res_srtp.so
#   ALL CHECKS PASSED: res_srtp.so is a valid aarch64 ELF module
```

## 涉及软件

- asterisk-srtp 22.10.1（及后续 asterisk 系列模块：res_pjsip 等）
- 任何 generate() 注入依赖到共享 SYS_PREFIX 的 autotools 配方

## 相关模式

- E052 / E060 — HMDFS 文件系统限制
- E002 — /tmp 只读（文件系统限制类）
- R26 — 系统同名库禁止动态链接

## 注意事项

1. **CI 结果判定**：以 CI 评论正文 Build Summary（Success/Failed）或 ci-wall 为准，
   不信 `ci-status` 的 "✅ PASSED" 字段（曾被证实是解析误导）
2. **本地"通过"可能是假象**：共享 SYS_PREFIX 有历史遗留库时本地能过、CI 干净环境暴露真实缺失
3. **补依赖要按 configure 报错顺序逐项来**：一次可能暴露多个，改完重新跑
4. 依赖包布局差异（.so vs .a、有无 .pc）需逐包确认后按实际校验

---
*doc/E332.md · knowledge graph draft · 2026-08-22 · contributor: 2301_80739235*
