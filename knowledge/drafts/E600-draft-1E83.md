# E600 — HMDFS setgid prevents mktemp from creating writable confstat dirs

## 错误签名
```
Permission denied ... confstat
confstat...Permission denied
cannot create...temporary directory
```

## 根因
The conan build dir (`b/`) on HMDFS is **setgid** (group=file_manager).
The vendor configure script uses:
```bash
umask 077 && mktemp -d -q ./confstatXXXXXX
```
On HMDFS, this creates confstat dirs with mode `0270` owned by uid `20001006`
(group=file_manager), **not** the build user (uid `20020101`).

Even though the build user is in the file_manager group, the setgid bit forces
the result to be owned by file_manager, and `0270` grants **no write
permission to the group**. HMDFS enforces owner-based permission checking
strictly, so the build user cannot write to its own temp dirs.
`chmod` does not help because HMDFS enforces the permission model at the
filesystem level.

## 识别特征
- **Severity**: 🟡 Medium
- **Trigger tool**: configure
- **Phase**: configuration
- **Pattern**: `umask 077.*mktemp|mktemp.*confstat`
- **Category**: hmdfs, build-system, portability

## 修复方案 (rec_approach: build-in-user-owned-dir)

### Step 1 — Copy source to a user-owned build root
```python
import shutil, os
build_root = "/storage/Users/currentUser/usr/nylon-build"
if os.path.exists(build_root):
    shutil.rmtree(build_root)
os.makedirs(build_root, 0o755)
# copy source tree into build_root...
```

### Step 2 — Patch configure to drop umask 077 → 022 and redirect confstat
```python
import subprocess
subprocess.run([
    "sed", "-i",
    "-e", "s|(umask 077|(umask 022|g",
    "-e", "s|./confstat$$-|%s/confstat$$-|g" % build_root,
    "-e", "s|./confstatXXXXXX|%s/confstatXXXXXX|g" % build_root,
    os.path.join(build_root, "configure"),
], check=True)
```

### Step 3 — Run configure/make/install from build script
```python
build_sh = os.path.join(self.generators_folder, "conanbuild.sh")
cmd = (
    "set -e\n"
    ". '%s'\n"
    "cd '%s'\n"
    "./configure ...\n"
    "make -j1\n"
    "make install\n"
) % (build_sh, build_root)
subprocess.run(["/data/service/hnp/bin/bash", "-c", cmd], ...)
```

## 参考实现
- `archives/n/nylon/1.21/conanfile.py` (nylon 1.21, HarmonyOS PC arm64)
- `knowledge/drafts/E600-draft-1E83.kv` (此条目的 .kv 格式)

## 验证方法
1. `stat` 确认 build_root 是 uid 20020101 且**无** setgid bit
2. `configure` 完成无 "Permission denied" 在 config.status 中
3. `make` 完成无 temp 文件操作的权限错误
4. `make install` 成功并生成可用的 binary
