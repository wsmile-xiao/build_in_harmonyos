# DRAFT-pico-sdk-test-package-absolute-pioasm：test_package 子脚本不要依赖 PATH 找 pioasm

> Contributor: pico-sdk 2.2.0 适配 | Status: Draft | Updated: 2026-08-25
> Source: shadow CI r3 fail / r4 pass

## 现象

pico-sdk shadow CI r3 中，`bin/pioasm` 已在 OHOS 上构建和安装，build 阶段 `pioasm --version` 也成功。但 test_package 的 `smoke.py` 报：

```text
FileNotFoundError: [Errno 2] No such file or directory: 'pioasm'
```

## 根因

`test_package/conanfile.py` 通过 `self.run(..., env="conanrun")` 包装了 Conan run env，但 OHOS 下又套了一层 `/data/service/hnp/bin/bash -lc`。Python 子脚本再用 `subprocess.run(["pioasm", ...])` 查 PATH，不如直接使用包内工具的绝对路径稳定。

日志里还出现：

```text
/data/service/hnp/bin/bash: /etc/profile: Permission denied
```

命令本身可继续成功，但这说明登录 shell 初始化不是可靠的测试前提。

## 推荐做法

在 test_package 中：

```python
pioasm_name = "pioasm.exe" if str(self.settings.os) == "Windows" else "pioasm"
pioasm_path = os.path.join(dep.package_folder, "bin", pioasm_name)
self._run_tool([sys.executable, smoke_script, pioasm_path, smoke_pio, smoke_header])
```

在 `smoke.py` 中只调用传入的绝对路径：

```python
subprocess.run([str(pioasm), "--version"], check=True)
```

## 验证证据

修改后 pico-sdk 2.2.0 shadow CI r4：L1 pass，test_package 执行 `smoke.py <package>/bin/pioasm ...`，`pioasm version: 2.2.0` 输出正常。