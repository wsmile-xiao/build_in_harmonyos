# E429 — OHOS 上可选 python-keyutils 不可用 / C 扩展在 CI 沙箱无法加载

## 错误特征
典型日志（`udiskie` 及其它依赖这些可选 C 扩展的纯 Python 包）：

```
ModuleNotFoundError: No module named 'keyutils'
```
或（C 扩展存在但无法加载）：
```
ImportError: Error relocating .../_gi.cpython-312-aarch64-linux-ohos.so:
             PyType_Ready: symbol not found
```

## 触发条件
- 构建系统: python（conan `package_type=application` / `python-require`）
- 阶段: testing / runtime
- 平台: OpenHarmony PC (aarch64)，CI worker 的 HNP python（AppSpawn 沙箱）

## 根因分析
1. `keyutils`（python-keyutils）是绑定 **libkeyutils / 内核 keyring** 的 C 扩展：
   - OHOS 制品仓与社区 PyPI 镜像（`pypi.cnb.cool`）仅有 sdist，**无 OHOS wheel**；
   - sdist 缺 `keyutils.h`（依赖 libkeyutils 开发头，系统无该系统库），pip 构建失败；
   - 内核 keyring 系统调用被沙箱阻止：ctypes 直调 arm64 `add_key`(syscall 248)
     → 进程被 kill（seccomp）。
2. 更普遍地，CI worker 的 python 处于 AppSpawn 沙箱，**无法 dlopen 用户空间 C 扩展
   `.so`**（`PyType_Ready` 重定位失败）。pygobject 的 `_gi.*.so` 即属此类；glib2 /
   gobject-introspection 在本仓也仅有静态库。
3. 因此任何"上游测试/功能运行期需要加载 C 扩展"的纯 Python 包，在本环境中会在
   导入阶段失败。

## 解决方案

### 推荐方案
- 判定该依赖/特性为**可选**（上游 `pyproject.toml` extra 或源码 `try/except` 守卫），
  保持惰性导入：缺失时如实降级（示例：`udiskie` 的 `udiskie.cache` 在 `cli.py:368`
  惰性导入，缺失只使 `--password-cache` 不可用，不影响其余功能，**不构成 R36 阻塞**）。
- 在上游测试报告中**如实计入"跳过/阻塞"**，并在 notes.md 写明根因与复验方式。
- 纯 Python 消费者的测试应避免在沙箱内导入 `gi`（参考 `alacarte` mock `gi` 先例）。
- 若确实需要该能力：**先立项适配**对应原生依赖（如 `keyutils`：C 扩展 + 内核 keyring
  能力），或由目标镜像提供 `gi`/typelib 运行期，再回归。

### 禁止做法
- ❌ 伪造 `keyutils`/`keyring` 的 dummy/stub 使上游测试"假通过"——破坏 R34/PF3 测试
  真实性门禁，审计失真一票否决。
- ❌ 用 `--build=missing` 或本地缓存绕过 R36 依赖闸。
- ❌ 在测试里硬编码"跳过"而不留证据；必须给出真实报错行。

## 验证
```bash
# 复现可选依赖缺失
python3 -c "import keyutils"
# 复现内核 keyring 被阻止（进程应被 kill）
python3 -c "import ctypes; ctypes.CDLL(None).syscall(248,b'user',b'k',None,1,-2)"
# 复现 gi C 扩展无法加载
PYTHONPATH=<pygobject>/lib/python3.12/site-packages python3 -c "import gi"
```

## 关联条目
- 相关: E524（依赖注入/前缀隔离）、undertime 先例（C 扩展依赖需纯 Python 或纯 Python 回退）
- 参考: `archives/u/udiskie/2.6.2/notes.md`
