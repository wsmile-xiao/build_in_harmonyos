# E570 — conan runner（self.run）在 HarmonyOS 上恒 SIGSEGV，test_package 必须改 subprocess

## 错误特征

`conan create` / `conan test` 走到 test_package 的 `test()` 时，**任何** `self.run(...)` 都失败，与命令内容无关：

```
ERROR: cpu/1.4.3@ohpcd/stable: Error in test() method
Error -11
```

其中 `-11` 即 SIGSEGV。实测探针结论（cpu 1.4.3）：连最简单的 `echo` 都返回 -11；同一台机器上手工执行同样命令、同样的 `sh` 与 bash，全部正常（`sh: alive`、`/data/service/hnp/bin/bash => alive`）。

## 触发条件

- 阶段: conan **test / test_package**（`test()` 方法内）
- API: 任何走 conan runner 的调用（`self.run`、`conanfile.run`）
- 环境: HarmonyOS（本平台）——与构建系统、语言、包类型无关
- 观察: 命令本身无错；换成 subprocess 立即恢复

## 根因分析

conan 的 runner 不直接 exec，而是把命令交给系统 `sh` 执行（本机 `sh` 为 mksh），由此路径在本平台上进程创建/信号处理异常，恒定以 SIGSEGV 结束。该故障发生在 conan 的 runner 层，**配方侧无法通过换 shell、改 `shell=True`、加 `set -e` 等手段规避**——因为选择执行器这一动作本身就发生在崩溃的那一层。

因此这是**平台级限制**而非某个包的适配缺陷：任何带 `test_package/` 的包，只要 `test()` 里用了 `self.run`，都会在 CI 上以同一个 `Error -11` 失败。它的误导性在于错误信息（Error -11）看起来像被测程序段错误，实际被测程序根本没被执行到。

## 解决方案

### 推荐方案

`test_package/conanfile.py` 的 `test()` 中改用 Python `subprocess` 直跑，自己准备环境变量：

```python
import os, shutil, subprocess

def test(self):
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ":" .join(self.deps_cpp_info.lib_paths + [env.get("LD_LIBRARY_PATH", "")])
    env["PATH"] = os.pathsep.join(self.deps_cpp_info.bindirs + [env.get("PATH", "")])
    env["CPU_TEST_ROOT"] = self.package_folder          # 包内自测所需的运行时根
    bash = shutil.which("bash") or "/bin/sh"
    subprocess.check_call([bash, "test.sh"], cwd=os.path.dirname(os.path.realpath(__file__)), env=env)
```

cpu 1.4.3 实测：改 subprocess 后 `11 passed, 0 failed`（本地与 conan create 均全绿）。

依赖信息取用注意：`self.deps_cpp_info` 在本平台可用；若不可用则退回 `self.dependencies[...].cpp_info` 或直接拼接 `package_folder`。

### 禁止做法

- ❌ 因 runner 崩而**削弱测试**：删掉 `test()` 体、把断言降级为 `print`、或 `exit 0` 了事（违反 R34：测试必须实质依赖被测包；PF3 前置硬闸会在建 PR 前拦截空壳 test）
- ❌ 把被测程序在 CI 上跳过、改为"本地已验证"的口头结论
- ❌ 在 test_package 里伪造测试输出（如打印"ALL PASSED"而不运行）

## 验证

```bash
# 同一 test_package：self.run 版本必挂，subprocess 版本必过
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify cpu 1.4.3
# 期望输出中包含
#   11 passed, 0 failed
```

## 关联条目

- 相关: E002（/tmp 只读，同属本平台环境限制类，对策均为"降级到可用路径"而非绕过）
- 相关: E046（HMDFS 权限语义失效）
