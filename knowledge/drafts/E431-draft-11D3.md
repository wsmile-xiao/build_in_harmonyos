# E431 — FUSE 挂载上 mkdtemp 的 0700 目录导致子进程 getcwd 失败

## 错误特征
```
configure: error: working directory cannot be determined
pwd: error retrieving current directory: getcwd: cannot access parent directories: Permission denied
```
（chdir 进入目录却可成功；`stat` 显示目录属主就是当前进程 uid）

## 触发条件
- 文件系统: /data/storage/el2（appdat）、/storage/Users（HMDFS）——两类 FUSE 均复现
- 场景: `tempfile.mkdtemp()`（0700）作为工作目录再派生 configure/sh
- 实证: `ohc clean-verify` 的 `ohc-verify-<sw>-<rand>/wmnd-<ver>`（G0 干净构建验证在 configure 阶段失败）
- 补充实测: `/data/service/hnp/bin/bash` 的 getcwd 在 0755 的 appdat 目录里
  **同样失败**（bundle bash / python3 / /system/bin/sh 均正常，SELinux 域同为
  develop_tools_hap）。ohc clean_verify.py:68 默认用它作 executable 跑 configure。

## 根因分析
这两类 FUSE 对目录 x 位的判定按"非属主"处理：即使目录是本进程创建的 0700，
子进程的 `getcwd()`（需读父目录项反查路径）也返回 EACCES。0700 换成 0755 后
`getcwd` 立即恢复（python/mksh 验证）。mkdtemp 按惯例创建 0700 目录，因此踩中。
/tmp、/dev/shm、/data/local/tmp 在本机均不可写，没有原生 FS 可绕。

## 解决方案

### 推荐方案（环境级，不改框架）
```sh
mkdir -p ~/.shimfix/pyshim
cat > ~/.shimfix/pyshim/sitecustomize.py <<'PY'
import os, tempfile
_orig = tempfile.mkdtemp
def _mkdtemp(*a, **kw):
    d = _orig(*a, **kw)
    try: os.chmod(d, 0o755)
    except OSError: pass
    return d
tempfile.mkdtemp = _mkdtemp
PY
export PYTHONPATH="$HOME/.shimfix/pyshim"
export TMPDIR=/data/storage/el2/base/cache   # chmod 在 el2/appdat 有效
export CONFIG_SHELL=/system/bin/sh           # 绕开 hnp bash 的 getcwd 缺陷
```

### 框架级正解（应另开 PR，勿混入软件 PR）
`scripts/ohc/clean_verify.py:82` 的 `tempfile.mkdtemp(...)` 后补
`os.chmod(tmpdir, 0o755)`；`:68` 的默认 CONFIG_SHELL 改为 /system/bin/sh。

### 禁止做法
- ❌ 在 /storage（HMDFS）上试图 chmod 修复——E046：chmod 被忽略，必须让 TMPDIR 指向 el2/appdat

## 验证
```bash
export PYTHONPATH="$HOME/.shimfix/pyshim"; export TMPDIR=/data/storage/el2/base/cache
export CONFIG_SHELL=/system/bin/sh
python3 scripts/ohc-run.py clean-verify wmnd 0.4.18   # G0 PASS（configure/make/install 全过）
```

## 关联条目
- 相关: E046（HMDFS chmod=0）、E429（SELinux 域导致的另一类 Permission denied）
