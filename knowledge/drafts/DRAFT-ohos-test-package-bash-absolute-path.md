# Conan test_package 的 test() 在 OHOS 需用绝对路径 bash

## Error signature

test_package 阶段执行 test() 时报 bash 不可用：

```text
======== Testing the package: Executing test ========
infgen/3.5 (test package): Running test()
infgen/3.5 (test package): RUN: bash "/storage/.../test_package/test.sh"
/system/bin/sh: bash: inaccessible or not found
ERROR: infgen/3.5 (test package): Error in test() method, line 20
	self.run(f'bash "{script}"', env="conanrun")
	ConanException: Error 127 while executing
```

## Root cause

OHOS profile 的 `[buildenv]` 里 `CONFIG_SHELL=/data/service/hnp/bin/bash` 与 `PATH`（含 `/data/service/hnp/bin`）只在 conan 的 **build 阶段**生效。test_package 的 `test()` 用 `env="conanrun"` 时，run 环境 PATH 只含 VirtualRunEnv 注入的 package bindirs，不含 `/data/service/hnp/bin`，因此 `self.run('bash ...')` 找不到 bash。

这与 E165（脚本 shebang 写 `#!/bin/bash` 失败）不同：这里不是脚本第一行的问题，而是 test() 里调用 bash 命令时 run 环境 PATH 缺失。

## Recommended fix

test() 中按平台选择 shell 绝对路径，并显式声明 VirtualRunEnv：

```python
class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.sh"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if str(self.settings.os) == "OHOS" or can_run(self):
            shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", shell)
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'{shell} "{script}"', env="conanrun")
```

## Validation evidence

infgen 3.5 shadow CI（真机 10.62.178.77，job `infgen-3.5-shadow-20260920`）：

- r2：`self.run(f'bash "{script}"', env="conanrun")` 报 `bash: inaccessible or not found`。
- 改为 OHOS 绝对路径 `/data/service/hnp/bin/bash` 后，r3 test_package 3/3 断言通过：

```text
infgen/3.5 (test package): RUN: /data/service/hnp/bin/bash ".../test.sh"
infgen 3.5
Usage:
! infgen 3.5 output
```

r3 全绿：`L0 pass / L1 pass / L2 skip / L4 pass / L5 pass`，exit code 0。

## Notes

- 若 test.sh 不含 bashism（`set -o pipefail` 等），可直接用 `sh`（`/system/bin/sh` 恒可用）作为 fallback。
- 参考先例：rgbds test_package 也用 `/data/service/hnp/bin/bash` + `CONFIG_SHELL` fallback。
