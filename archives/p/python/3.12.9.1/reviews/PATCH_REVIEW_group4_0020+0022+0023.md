# 补丁审查报告 — Group 4: 0020 + 0022 + 0023

## 0020 - missing-scan-fixups-HarmonyOS（聚合修复，6 个子修改）

**结论**: ✅ 必要（部分子项可优化）

### 0020-a: pylifecycle.c `is_valid_fd()` 添加 `__OHOS__`

**现状分析**:
```c
// 3.12.9 已补丁后的代码 (L2335-2341):
#if defined(F_GETFD) && ( \
        defined(__linux__) || \
        defined(__APPLE__) || \
        defined(__OHOS__) || \      // ← 补丁添加
        defined(__wasm__))
    return fcntl(fd, F_GETFD) >= 0;
#elif defined(__linux__) || defined(__OHOS__)   // ← 补丁添加
    int fd2 = dup(fd);
```

**审查意见**: ✅ **必要**。pyconfig.h 中 `HAVE_FCNTL_H=1`，`F_GETFD` 宏可用。不加 `__OHOS__` 则 `is_valid_fd()` 走不到任何条件分支（既非 `__linux__` 也非 `__APPLE__`），会导致未定义行为。`fcntl(F_GETFD)` 比 `dup()` 更优（不会 EMFILE）。

---

### 0020-b: shutil.py sendfile 启用

**现状分析**:
```python
# 3.12.9 已补丁后 (L51):
_USE_CP_SENDFILE = hasattr(os, "sendfile") and sys.platform.startswith(("linux", "ohos"))
```
**关键发现**: pyconfig.h 中 `HAVE_SENDFILE=1`，即 configure 已检测到 `sendfile(2)`。`os.sendfile` 在 Python 层可用。

**审查意见**: ✅ **必要**。因为 `sys.platform == 'ohos'`（不是 `'linux'`），原代码 `startswith("linux")` 会跳过 sendfile 优化。但有一个隐患：

> **⚠️ 可优化**: 鸿蒙的 `sendfile(2)` 语义是否与 Linux 完全一致？如果偏移量参数 `offset` 处理不同，可能导致数据损坏。建议首次运行时用 `shutil.copyfile()` 做基准对比测试验证。如果语义不一致，应该去掉 `'ohos'`，让 shutil 走 read/write 路径（更安全但更慢）。

---

### 0020-c: tempfile.py 临时目录

**现状分析**:
```python
# 3.12.9 已补丁后 (L172-175):
elif _sys.platform.startswith(('ohos', 'harmonyos')):
    dirlist.extend(['/tmp', '/data/local/tmp', '/var/tmp'])
else:
    dirlist.extend([ '/tmp', '/var/tmp', '/usr/tmp' ])
```

**审查意见**: ⚠️ **可优化**。

1. **多余分离**: ohos 分支的列表 `['/tmp', '/data/local/tmp', '/var/tmp']` 与 else 分支 `['/tmp', '/var/tmp', '/usr/tmp']` 高度重叠。唯一新增路径是 `/data/local/tmp`。
2. **`/data/local/tmp` 是 Android 惯例，非鸿蒙**: 鸿蒙设备不一定有此路径。
3. **建议方案**: 可以直接走 else 分支，不需要单独的 ohos 分支。如果确实需要额外路径，只需在 else 分支通用处理即可。

```python
# 建议简化为: 不需要这个修改，删除即可
```

---

### 0020-d: uuid.py MAC 地址查找路径

**现状分析**:
```python
# 3.12.9 已补丁后 (L364-368):
path_dirs = os.environ.get('PATH', os.defpath).split(os.pathsep)
path_dirs.extend(['/sbin', '/usr/sbin'])
if sys.platform.startswith(('ohos', 'harmonyos')):
    path_dirs.extend(['/system/bin', '/bin'])
```
`_find_mac_near_keyword` 会依次尝试 `ifconfig`、`ip`、`arp`、`netstat` 等命令。

**审查意见**: ⚠️ **可优化（低优先级）**。

1. 鸿蒙的 `$PATH` 通常已包含 `/system/bin`（`os.defpath` 在 0012 补丁中也已加了 `/system/bin`）。
2. 如果 PATH 设置正确，`shutil.which` 已经能找到 `/system/bin/ifconfig`，无需额外添加。
3. 但作为防御性编程，保留无副作用。**建议保留但标记为低优先级**。

---

### 0020-e: configure.ac / configure lchmod 跳过

**现状分析**:
```shell
# 3.12.9 已补丁后 (configure.ac L4948):
if test "$MACHDEP" != linux && test "$MACHDEP" != ohos; then
  AC_CHECK_FUNCS([lchmod])
fi
```
原代码只有 `test "$MACHDEP" != linux`，补丁增加了 `&& test "$MACHDEP" != ohos`。

**审查意见**: ✅ **必要**。但有一个**组织问题**:

> **⚠️ 注意**: 这个修改不在 0003 configure.ac 补丁文件中，是直接编辑到源码树上的。如果重新从头应用补丁，这个修改会丢失。**建议合并到 0003 补丁中**，而不是放在 0020 聚合补丁里。理由：lchmod 跳过属于 configure 阶段逻辑，应与其他 platform detection 放在一起。

---

## 0022 - compileall.py HMDFS hardlink 回退

**结论**: ✅ 必要

**现状分析**:
```python
# 3.12.9 已补丁后 (L252-262):
if filecmp.cmp(cfile, previous_cfile, shallow=False):
    try:
        os.unlink(cfile)
        os.link(previous_cfile, cfile)
    except OSError:
        if sys.platform == 'ohos':
            shutil.copy2(previous_cfile, cfile)
        else:
            raise
```
HMDFS 不支持 `hardlink(2)`，调用 `os.link()` 会抛 OSError。

**审查意见**: ✅ **必要，方案合理**。

- compileall 在编译 .pyc 时会尝试 hardlink 相同内容（level 0 和 level 1 的 .pyc 内容通常一样），HMDFS 上会失败。
- `try/except OSError` 是 Python 标准的做法（PEP 384 兼容层也用类似模式）。
- 无法在 `os.link` 层面做全局 HMDFS 适配（那会影响所有 hardlink 调用，副作用太大）。

> **⚠️ 小优化**: `sys.platform == 'ohos'` 用的是精确匹配，而 0013 和其他补丁用的是 `startswith(('ohos', 'harmonyos'))`。建议统一为 `sys.platform.startswith(('ohos', 'harmonyos'))` 以保持一致性。虽然目前 sys.platform 固定返回 `'ohos'`，但用 startswith 更防御。

---

## 0023 - ctypes/util.py ldconfig 守卫

**结论**: ✅ 必要

**现状分析**:
```python
# 3.12.9 已补丁后 (L273-276):
def _findSoname_ldconfig(name):
    # HarmonyOS has no /sbin/ldconfig
    if sys.platform.startswith(('ohos', 'harmonyos')):
        return None
    import struct
```
另有 3 处 `/sbin/ldconfig` 引用：
- L93: 注释 "using gcc, /sbin/ldconfig, objdump" — 仅文字描述，无影响
- L215: `Popen(('/sbin/ldconfig', '-r')...)` — 在 AIX 专属代码块内（`if os.name == "posix" and sys.platform == "darwin"` 的后续 elif 分支），鸿蒙不会走到
- L295: `Popen(['/sbin/ldconfig', '-p']...)` — 在 `_findSoname_ldconfig` 内部，已被 L275 守卫拦截

**审查意见**: ✅ **必要，覆盖完整**。守卫放在函数入口，后续所有 `/sbin/ldconfig` 调用都被跳过。AIX 路径的 L215 不会到达（被 `sys.platform` 条件排除）。

---

## 总结表格

| 补丁 | 子项 | 结论 | 备注 |
|------|------|------|------|
| 0020 | pylifecycle.c is_valid_fd | ✅ 必要 | — |
| 0020 | shutil.py sendfile | ✅ 必要 | ⚠️ 需验证鸿蒙 sendfile 语义 |
| 0020 | tempfile.py 临时目录 | ⚠️ 可优化 | /data/local/tmp 非鸿蒙路径，建议删除此子项 |
| 0020 | uuid.py MAC 查找 | ⚠️ 可优化 | PATH 通常已含 /system/bin，保留也无害 |
| 0020 | configure lchmod | ✅ 必要 | ⚠️ 应合并到 0003，而非放在 0020 |
| 0022 | compileall.py hardlink | ✅ 必要 | 建议统一 sys.platform 检测方式为 startswith |
| 0023 | ctypes/util.py ldconfig | ✅ 必要 | 覆盖完整 |
