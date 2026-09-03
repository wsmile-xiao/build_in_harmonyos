# E999: pip生成的console script shebang不可迁移

## 错误特征

- **触发工具**: python, pip
- **出错阶段**: installation, packaging
- **严重程度**: 🟡 medium (2)
- **分类**: python, portability, packaging

## 问题描述

pip install 生成的 console script（位于 `bin/` 目录）的 shebang 行硬编码了构建机的 Python 绝对路径（如 `#!/usr/bin/python3.12` 或 `#!/path/to/venv/bin/python3`），导致打包后的命令在不同 Worker 或用户环境中无法执行。

## 根因分析

1. pip 根据当前 Python 解释器的 `sys.executable` 生成 shebang
2. 该路径是构建时的绝对路径，打包后该路径在消费者环境不存在
3. Conan 包应该是自包含的，不应依赖构建机特定路径

## 典型错误日志

```
bash: /usr/bin/python3.12: No such file or directory
# 或在测试中
subprocess.CalledProcessError: Command '['cpuinfo', '--version']' returned non-zero exit status 127
```

## 影响范围

所有声明 `console_scripts` 或 `entry_points` 的 Python 包，包括但不限于：
- py-cpuinfo
- 其他提供 CLI 工具的 Python 库

## 推荐解决方案（优先级 1）

**方法**: 在 `conanfile.py` 的 `package()` 方法中改写 shebang 为可迁移的 shell wrapper

```python
def package(self):
    # pip install 到 staging
    self.run(f"python3 -m pip install --no-deps --prefix={self.package_folder} ...")
    
    # 改写 console script shebang
    for script in ["cpuinfo"]:  # 替换为实际的命令名
        script_path = os.path.join(self.package_folder, "bin", script)
        if os.path.exists(script_path):
            # 读取模块名（从 setup.py entry_points 获取）
            module_name = "cpuinfo"  # 实际模块名
            wrapper = f"""#!/bin/sh
exec python3 -m {module_name} "$@"
"""
            with open(script_path, "w") as f:
                f.write(wrapper)
            os.chmod(script_path, 0o755)
```

**原理**: 
- 使用 `#!/bin/sh` + `exec python3 -m <module>` 间接调用
- `python3` 由系统 PATH 解析，不依赖绝对路径
- `-m` 模块执行方式等价于直接调用，但更可移植

## 回退方案（优先级 2）

如果无法确定模块名，使用 `#!/usr/bin/env python3`：

```python
import fileinput
for line in fileinput.input(script_path, inplace=True):
    if fileinput.filelineno() == 1:
        print("#!/usr/bin/env python3")
    else:
        print(line, end='')
```

**注意**: 此方案依赖消费者环境的 PATH 配置，不如方案 1 自包含。

## 禁止做法

❌ **保留 pip 生成的原始 shebang**
- 后果：命令在消费者环境无法执行，`conan test_package` 的 CLI 验证失败

❌ **假设命令在系统 PATH 中**
- 后果：消费者需要手动 `export PATH` 或执行 `activateConanRunEnvironment.sh` 才能使用 CLI

## 验证方法

1. **本地验证**:
   ```bash
   conan create . --build=missing
   head -1 ~/.conan2/p/<pkg>/<hash>/p/bin/<cmd>  # 检查 shebang
   ~/.conan2/p/<pkg>/<hash>/p/bin/<cmd> --version  # 直接执行
   ```

2. **test_package 验证**:
   ```python
   # test_package/test_cpuinfo.py
   import subprocess
   from pathlib import Path
   
   # 通过包内绝对路径验证（不依赖 PATH）
   cli_path = Path(__file__).parents[4] / "bin" / "cpuinfo"
   result = subprocess.run([str(cli_path), "--version"], 
                          capture_output=True, text=True, check=True)
   assert result.returncode == 0
   ```

## 相关原则

- **P007**: 可移植性优先（路径、环境变量、系统依赖）

## 案例

- **py-cpuinfo 9.0.0** (PR #7675): 
  - 问题：pip 生成的 `cpuinfo` 命令 shebang 为 `/usr/bin/python3.12`
  - 解决：改写为 `#!/bin/sh\nexec python3 -m cpuinfo "$@"`
  - CI 验证：构建 #36790 通过

## 参考资料

- py-cpuinfo conanfile.py: `archives/p/py-cpuinfo/9.0.0/conanfile.py`
- Python Packaging User Guide: https://packaging.python.org/en/latest/specifications/entry-points/

---

**贡献者**: AtomCode <noreply@atomgit.com>  
**来源 PR**: #7675  
**提交**: fe8cd686e8  
**最后更新**: 2026-09-02
