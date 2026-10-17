# DRAFT-4033-binwalk-2.3.4 — OHOS 捆绑 Python：subprocess 裸名不走 PATH 搜索 + pwd.getpwuid KeyError

> 草稿（待审核 promote）。来源：binwalk/2.3.4 适配（PR #4033，补丁 0003）。

## 错误特征

```
FileNotFoundError: [Errno 2] No such file or directory: 'tar'
KeyError: 'getpwuid(): uid not found: 20020101'
```

典型症状：
- 同一命令在 shell（bash/zsh/curl）中正常，仅从 Python `subprocess.call(['tar', ...])`
  裸名调用失败
- 带 "非 root 检查"（`pwd.getpwuid`）的上游代码在模块加载时崩溃
  （binwalk 表现为 `Failed to load Extractor module`，`binwalk -e` 全断）

## 触发条件

- 构建系统: 任意（纯 Python 包最常见）
- 阶段: runtime / testing（conan test_package、上游测试套件、CLI 实测）

## 根因分析

1. **subprocess 裸名不走 PATH**：HNP 打包的 Python 3.12 对
   `…/lib/python3.12/subprocess.py` 打了 `_IS_HARMONYOS` 补丁——executable
   不含目录前缀时也走 `os.posix_spawn()`；而 musl 的 `posix_spawn`（非
   `posix_spawnp` p 变体）对不含 `/` 的路径**不做 PATH 搜索**，按相对 CWD
   执行 `execve('tar')` → `ENOENT`。`shutil.which()` 逐目录检查
   `os.access(X_OK)` 不受影响；`shell=True` 由 shell 自己查 PATH 也不受影响。
2. **getpwuid KeyError**：OHOS 沙箱 uid（如 20020101）可能没有 passwd 数据库
   条目，`pwd.getpwuid()` 抛 `KeyError`；上游惯用 `user_info.pw_uid == 0` 做
   root 检查的代码直接崩溃。

## 解决方案

### 推荐方案

源码 portability 补丁（不用 `__OHOS__` 宏——try/except 与 shutil.which 本身
就是跨平台通用修复，见 R8）：

```python
# 1. 外部命令预解析绝对路径
cmd_list = shlex.split(command)
if cmd_list and not os.path.dirname(cmd_list[0]):
    resolved = shutil.which(cmd_list[0])
    if resolved:
        cmd_list[0] = resolved
rval = subprocess.call(cmd_list, stdout=tmp, stderr=tmp)

# 2. getpwuid 回退进程凭据；root 检查改用 os.getuid()
try:
    user_info = pwd.getpwuid(os.getuid())
except KeyError:
    user_info = None
if os.getuid() == 0:
    raise ModuleException(...)
self.runas_uid = user_info.pw_uid if user_info else os.getuid()
self.runas_gid = user_info.pw_gid if user_info else os.getgid()
```

参考实现：`archives/b/binwalk/2.3.4/patches/0003-src-binwalk-modules-extractor.py.patch`

### 禁止做法

- ❌ 裸名 `subprocess.call(['tar', ...])` 失败后直接判 "工具未安装"（误诊）
- ❌ 用 `__OHOS__` 平台宏守卫此类修复（R8：修复本身是通用健壮性改进）

## 验证

```bash
# 复现（OHOS 捆绑 Python 上）:
python3 -c "import subprocess; subprocess.call(['tar','--version'])"        # FileNotFoundError
python3 -c "import subprocess; subprocess.run('tar --version', shell=True)" # OK

# 修复后（binwalk 2.3.4 实测）:
binwalk -e firmware.gzip   # 提取链路正常，上游 test_dirtraversal PASS
```

## 关联条目

- 相关: E212（HNP 进程 dlopen 限制，同属 HNP Python 平台特性）、E077
- 案例: binwalk/2.3.4 PR #4033（补丁 0003；上游测试 5/7 → 6/7）
