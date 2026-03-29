# CPython 3.9 rename & symlink 调用链分析

> **源码**: Python 3.9.0 (`~/python/Python-3.9.0-clean-v5`)
> **分析日期**: 2026-03-27
> **目的**: 理解 rename/symlink 在 CPython 中的完整实现链路，定位鸿蒙上失败的根本环节

---

## 一、os.rename / os.replace 完整调用链

```
┌──────────────────────────────────────────────────────────────────────┐
│  Python 层入口                                                       │
│                                                                      │
│  os.rename(src, dst)     os.renames(old, new)     os.replace(src,dst)│
│  (C 模块直接导出,         (Python 包装,             (C 模块直接导出,    │
│   os.py 中无定义)          内部调用 os.rename)       os.py 中无定义)    │
│         │                       │                        │           │
└─────────┼───────────────────────┼────────────────────────┼───────────┘
          │                       │                        │
          ▼                       ▼                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│  C 层 (Modules/posixmodule.c)                                       │
│                                                                      │
│  os_rename_impl() :4362       os_replace_impl() :4383               │
│       │                              │                               │
│       └──────────┬───────────────────┘                               │
│                  ▼                                                   │
│       internal_rename(src, dst, ..., is_replace)  :4285              │
│                  │                                                   │
│       ┌──────────┴──────────┐                                        │
│       │ #ifdef MS_WINDOWS   │                                        │
│       │   MoveFileExW()     │                                        │
│       │ #else               │                                        │
│       │  #ifdef HAVE_RENAMEAT                                        │
│       │   renameat()        │  ← dir_fd 指定时                       │
│       │  #else              │                                        │
│       │   rename()          │  ← 标准 POSIX 系统调用                  │
│       │  #endif             │                                        │
│       └──────────┬──────────┘                                        │
└──────────────────┼───────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Linux/鸿蒙 内核                                                      │
│                                                                      │
│  rename(2)     或    renameat(2)                                     │
│  (fs/namei.c: vfs_rename)                                           │
└──────────────────────────────────────────────────────────────────────┘
```

### 关键发现

1. **os.rename 和 os.replace 在 C 层共享同一个 `internal_rename()` 函数**（:4285），区别仅 `is_replace` 参数
2. **rename 和 replace 在 POSIX 上都调用同一个 `rename(2)` 系统调用** — POSIX rename(2) 本身支持覆盖目标
3. **`HAVE_RENAMEAT` 条件编译**: 有 `dir_fd` 时走 `renameat(2)`，否则走 `rename(2)`
4. **rename 路径没有任何 `__OHOS__` 特殊处理**，完全走标准 POSIX 路径
5. `os.renames()` 是纯 Python 包装（os.py:254），递归创建目标目录后调用 `os.rename()`

### posixmodule.c 中 rename 相关代码位置

| 函数 | 位置 | 说明 |
|------|------|------|
| `internal_rename()` | posixmodule.c:4285 | 核心实现，处理 rename/replace 两种模式 |
| `os_rename_impl()` | posixmodule.c:4362 | os.rename 入口，调用 `internal_rename(..., 0)` |
| `os_replace_impl()` | posixmodule.c:4383 | os.replace 入口，调用 `internal_rename(..., 1)` |
| `renameat()` 调用 | posixmodule.c:4330 | `#ifdef HAVE_RENAMEAT` 条件分支 |
| `rename()` 调用 | posixmodule.c:4335 | 无 dir_fd 时直接调用 |
| `HAVE_RENAMEAT` 导出 | posixmodule.c:14801 | 功能检测常量导出到 Python |

---

## 二、os.symlink / os.readlink / os.link 完整调用链

```
┌──────────────────────────────────────────────────────────────────────┐
│  Python 层入口                                                       │
│                                                                      │
│  os.symlink(src, dst, ...)       os.readlink(path, ...)              │
│  os.link(src, dst, ...)          (均从 posix 模块 C 实现代理)         │
└─────────┼─────────────────────────────────┼──────────────────────────┘
          │                                 │
          ▼                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  C 层 (Modules/posixmodule.c)                                       │
│                                                                      │
│  os_symlink_impl() :8264         os_readlink_impl() :8065            │
│    │ HAVE_SYMLINKAT → symlinkat()    │ HAVE_READLINKAT → readlinkat() │
│    │ else → symlink()                │ else → readlink()              │
│                                                                      │
│  os_link_impl() :3658                                               │
│    │ HAVE_LINKAT → linkat()                                         │
│    │ else → link()                                                   │
└─────────┼─────────────────────────────────┼──────────────────────────┘
          │                                 │
          ▼                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Linux/鸿蒙 内核                                                      │
│                                                                      │
│  symlink(2) / symlinkat(2)        readlink(2) / readlinkat(2)        │
│  link(2) / linkat(2)                                               │
└──────────────────────────────────────────────────────────────────────┘
```

### posixmodule.c 中 symlink 相关代码位置

| 函数 | 位置 | 系统调用 |
|------|------|---------|
| `os_symlink_impl()` | posixmodule.c:8264 | `symlink(2)` / `symlinkat(2)` |
| `os_readlink_impl()` | posixmodule.c:8065 | `readlink(2)` / `readlinkat(2)` |
| `os_link_impl()` | posixmodule.c:3658 | `link(2)` / `linkat(2)` |

### symlat/readlinkat 引用位置

| 行号 | 内容 | 类型 |
|------|------|------|
| 8053 | `dir_fd(requires='readlinkat')` | Clinic 注解 |
| 8073-8075 | `readlinkat(dir_fd, path, buffer, MAXPATHLEN)` | 调用 |
| 8245 | `dir_fd(requires='symlinkat')` | Clinic 注解 |
| 8337-8340 | `symlinkat(src, dir_fd, dst)` | 调用 |

---

## 三、各使用场景调用路径与鸿蒙风险

### 3.1 compileall（.pyc 原子写入）

```
compileall.compile_file()
  └→ py_compile.compile()                     (Lib/py_compile.py:79)
      └→ importlib._bootstrap_external._write_atomic()  (行 120)
          ├→ os.open(path_tmp, O_EXCL|O_CREAT|O_WRONLY)   ← 创建临时文件
          ├→ FileIO(fd, 'wb').write(data)                   ← 写入字节码
          └→ os.replace(path_tmp, path)                     ← ★ 原子 rename
              └→ internal_rename() :4285 → rename(2)
```

**鸿蒙风险**：
- `os.replace()` 走标准 `rename(2)` 路径
- 如果临时文件和 `__pycache__` 在不同分区，`rename(2)` 返回 `EXDEV`
- 测试中观察到的 `Operation not permitted`（errno=EPERM）更可能是 **SELinux 对文件类型变更的限制**（rename 同一文件系统内执行但被安全策略拒绝）

### 3.2 import（.pyc 自动写入）

```
import 语句
  └→ SourceFileLoader.set_data()
      └→ _write_atomic(path, data, _mode)   (行 120)
          ├→ os.open(path_tmp, ...)
          └→ os.replace(path_tmp, path)      ← ★ 同 compileall
              └→ internal_rename() :4285 → rename(2)
```

**鸿蒙风险**：
- `_write_atomic` 中 `os.replace()` 失败被 catch 后静默忽略（不 crash），但每次 import 都需重新编译
- 测试中 test_import 的 crash 发生在 `_rmtree_inner` 删除 `.pyc` 文件时（Permission denied），不是 rename 本身

### 3.3 shutil.move（文件/目录移动）

```
shutil.move(src, dst)                       (Lib/shutil.py:803)
  ├→ os.rename(src, real_dst)               ← 主路径
  │   └→ os_rename_impl() :4362 → rename(2)
  └→ (OSError 回退)                          (行 804-814)
      ├→ if symlink: os.symlink() + os.unlink()
      ├→ if directory: copytree() + rmtree()
      └→ if file: copy_function() + os.unlink()
```

**鸿蒙风险**：
- `os.rename()` 失败有回退机制，相对安全
- 但回退中 `os.symlink()` 也会失败（HMDFS 不支持）
- 最终 fallback 到 `copy + unlink`，此路径最安全但性能最低

### 3.4 shutil.copy2 / copytree（symlink 复制）

```
shutil.copy2(src, dst, follow_symlinks=False)   (行 256-259)
  └→ if _islink(src):
      os.symlink(os.readlink(src), dst)          ← ★ symlink 创建

shutil.copytree(src, dst, symlinks=True)         (行 474-479)
  └→ os.readlink(srcname)
      os.symlink(linkto, dstname)                 ← ★ symlink 创建
```

**鸿蒙风险**：⚠️ 无 fallback，symlink 创建直接失败

### 3.5 pathlib.Path

```
Path.rename(target)    → _accessor.rename() → os.rename()   (pathlib.py:1367)
Path.replace(target)   → _accessor.replace() → os.replace() (pathlib.py:1379)
Path.symlink_to(target) → accessor.symlink() → os.symlink()  (pathlib.py:1393)
Path.readlink()        → accessor.readlink() → os.readlink() (pathlib.py:1277)
```

**鸿蒙风险**：
- rename/replace: 同 os.rename() 风险
- symlink_to(): ⚠️ 无 fallback

### 3.6 venv（虚拟环境创建）

```
python -m venv ENV
  └→ EnvBuilder.create()
      ├→ create_configuration() :138-149
      │   ├→ os.symlink('lib', link_path)        ← lib64 → lib
      │   │   except OSError:                      ← ★ 补丁 0021 已加 fallback
      │   │   os.makedirs(link_path)               ← makedirs 替代
      │   └→ symlink_or_copy() :178-195
      │       ├→ os.symlink(src, dst)              ← bin/python 等
      │       └→ except Exception:                  ← ★ 内置 fallback
      │           shutil.copyfile(src, dst)
```

**鸿蒙风险**：✅ 已修复 — 补丁 0021 覆盖了 lib64 fallback，symlink_or_copy 有内置 fallback

### 3.7 tempfile

```
tempfile.mkstemp()
  └→ _mkstemp_inner()
      └→ os.open(file, O_EXCL|O_CREAT)   ← 不涉及 rename
```

**鸿蒙风险**：✅ 低 — 仅依赖 open(2) 和 unlink(2)

---

## 四、鸿蒙失败根因总结

### 4.1 rename 失败的根因

| errno | 含义 | 鸿蒙特定原因 | 影响场景 |
|-------|------|-------------|---------|
| **EPERM** | Operation not permitted | SELinux 策略限制对 .pyc 文件类型执行 rename | compileall (.pyc→.opt-1.pyc) |
| **EXDEV** | Invalid cross-device link | TMPDIR 和源码在不同分区 | _write_atomic (临时文件 rename) |
| **EACCES** | Permission denied | 沙箱对某些目录的写权限受限 | 跨目录 rename |
| **ENOENT** | No such file or directory | 目标父目录不存在 | 正常情况，非鸿蒙特定 |

**关键洞察**: 测试中 compileall 的 `Operation not permitted` 是 **EPERM**（不是 EXDEV），说明 rename 在同一文件系统内执行但被安全策略拒绝。这指向鸿蒙 SELinux 对**文件 rename 操作**本身的限制，而非跨分区问题。

### 4.2 symlink 失败的根因

| errno | 含义 | 鸿蒙特定原因 | 影响场景 |
|-------|------|-------------|---------|
| **EPERM** | Operation not permitted | HMDFS 不支持 symlink（SELinux + Hmmac） | venv, shutil, pathlib, tarfile |

### 4.3 link (硬链接) 失败的根因

| errno | 含义 | 鸿蒙特定原因 | 影响场景 |
|-------|------|-------------|---------|
| **EPERM** | Operation not permitted | SELinux 策略禁止硬链接 | compileall pyc 去重, shutil.move 回退 |
| **EXDEV** | Invalid cross-device link | 跨文件系统不支持硬链接 | 跨分区 link |

---

## 五、`__OHOS__` 条件编译总览

在 **rename/symlink 路径中没有** 任何 `__OHOS__` 特殊处理。

`__OHOS__` 出现在以下位置（与 rename/symlink 无关）：

| 文件 | 行号 | 说明 |
|------|------|------|
| posixmodule.c | 9440 | sendfile offset=NULL 优化 |
| _posixsubprocess.c | 49 | FD_DIR=/dev/fd |
| timemodule.c | 513,564,1850 | musl 时区处理 |
| pylifecycle.c | 1757 | dup() fd 校验 |
| pythread.h | 28 | PY_HAVE_THREAD_NATIVE_ID |
| thread_pthread.h | 16,335 | syscall(SYS_gettid) |

---

## 六、已覆盖 vs 未覆盖

### ✅ 已有补丁覆盖

| 场景 | 补丁 | 策略 |
|------|------|------|
| venv lib64 → lib | 0021 | `os.symlink` except → `makedirs` |
| venv bin/python | 内置 | `symlink_or_copy` except → `shutil.copyfile` |
| make install libpython.so | 0024 | `cp -p` 代替 `ln -s` |

### ❌ 未覆盖（可能需要额外修复）

| 场景 | 调用位置 | 建议 |
|------|---------|------|
| `_write_atomic` rename 失败 | importlib._bootstrap_external:120 | 添加 rename 失败后的 fallback（直接 write 而非 rename） |
| `pathlib.Path.symlink_to()` | pathlib.py:1393 | 添加 try/except + copy fallback |
| `shutil.copy2(follow_symlinks=False)` | shutil.py:259 | symlink 失败时 fallback 到 copy |
| `shutil.copytree(symlinks=True)` | shutil.py:479 | symlink 失败时 fallback 到 copy |
| `shutil.move()` symlink 回退 | shutil.py:807 | symlink 重建失败时 fallback 到 copy |
| `compileall` pyc 硬链接 | compileall.py:245 | link() 失败已有 except 处理，无需修改 |
