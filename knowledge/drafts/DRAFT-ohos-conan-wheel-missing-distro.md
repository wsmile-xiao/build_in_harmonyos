# DRAFT-ohos-conan-wheel-missing-distro — 社区源 conan wheel 在 OHOS 缺 distro，conan 启动即崩

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-14 | Severity: 🟡 medium
> Source: libiodbc2 3.52.16 适配时 `ci/conan/setup.sh` 首次运行失败

## Symptom

`bash ci/scripts/preflight_check.sh` / `ohc-run.py finish` 依赖的
`ci/conan/setup.sh` 会 `pip install --user` 社区源 conan wheel；安装“成功”后仍然：

```text
[step] Conan version: unknown
[error] conan 仍然无法运行, 诊断系统环境...
[error] Conan 无法启动, Worker 环境需要修复 (非 CI 脚本问题)
```

手工执行安装出的入口脚本可见真实首错：

```text
$ ~/.local/bin/conan --version
  File ".../conan/api/conan_api.py", line 152, in _init_global_conf
    self.global_conf = load_global_conf(self._conan_api.home_folder)
  File ".../conan/internal/model/conf.py", line 793, in load_global_conf
    import distro
ModuleNotFoundError: No module named 'distro'
```

`setup.sh` 的 `conan --version 2>/dev/null || echo unknown` 把 stderr 吞掉，
只留下 `Conan version: unknown` + “Worker 环境需要修复”，因此现场很难定位。

## Root Cause

conan 2.29.1 的 wheel METADATA 声明：

```
Requires-Dist: distro<2.0.0,>=1.4.0; platform_system == "Linux" or platform_system == "FreeBSD"
```

OHOS 上 `platform.system()` 不返回 `Linux`/`FreeBSD`，**该环境标记不成立 → pip 不安装 distro**；
而 conan 代码在 `load_global_conf()` 里无条件 `import distro`，启动即崩。
即“依赖声明写了却没装”，不是缺包源问题（同一 wheel 在其他平台自动带上 distro）。

旁证：AgentCode/OpenDesk 运行时自带的解释器前缀
（`~/.opendesk/interpreters/pip-global`）里存在 `distro-1.9.0.dist-info`，
说明正常预置的 OHOS 工具链环境是带 distro 的，只有 `pip install --user` 这条路径会漏。

## Recommended Solution

装一次 `distro` 即可（`--user` 与 conan 同前缀，`setup.sh` 的 `--force-reinstall conan`
不会移除它，故一次修复长期有效）：

```bash
python3 -m pip install --user distro
~/.local/bin/conan --version      # → Conan version 2.29.1
```

修复后 `bash ci/conan/setup.sh` rc=0（实测约 12s，输出 `Conan environment ready ✅`）。

**对 CI 脚本/工具链的建议（框架侧，需单独 PR）**：
- `setup.sh` 在 `--force-reinstall conan` 之后补一步 `python3 -m pip install --user distro`
  （或把 `Conan version: unknown` 的判定改为打印 conan 的 stderr 首行），
  否则每次新 worker 都会重现且现场无有效报错；
- 或在社区源 wheel 的依赖里补上 OHOS 的情况。

## 单库实证

- 环境：OHOS PC worker，python 3.12.9（HNP），社区源 `pypi.cnb.cool`；
- 修复前：`conan --version` → `ModuleNotFoundError: No module named 'distro'`；
- 修复后：`Conan version 2.29.1`；`ci/conan/setup.sh` rc=0；`conan remote list` 可见
  `ohpcd` remote、profile `ohos-aarch64` 就绪；
- 关联：本条是 libiodbc2 W3 阻塞链的第一段（后两段见
  `DRAFT-autotools-perl-tmpdir-candidate-vetting` 与 notes.md）。
