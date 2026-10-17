# E604 — Conan test_package 的 Bash 配置回退

## 错误特征

平台 CI 的 Conan test package 日志出现：

```text
RUN: "None" .../hamlib-test-command.sh
/system/bin/sh: None: inaccessible or not found
Error 127 while executing
```

包本身已经完成编译和打包，但测试包在调用生成的 shell 脚本时失败。

## 触发条件

- 构建系统：Conan 2 recipe/test_package
- 阶段：test_package build
- 场景：OHOS host 与 Windows build profile 分离，CI 没有提供 `tools.microsoft.bash:path`

## 根因分析

配方只读取 `tools.microsoft.bash:path`，并把结果直接插入 `self.run()`。该 conf 在本地 Windows profile 中存在，但不是所有平台 worker 的必选配置；缺失时 Conan 返回空值，格式化命令后变成字面量 `None`。因此 CI shell 找不到名为 `None` 的可执行文件，产生 RC 127。这是命令选择边界问题，不是目标包编译失败。

## 解决方案

### 推荐方案

在读取可选 Bash 路径时提供命令名回退，同时保留显式路径：

```python
bash = self.conf.get(
    "tools.microsoft.bash:path", default="bash", check_type=str
) or "bash"
self.run(f'"{bash}" "{command_script}"')
```

本地 profile 可以继续提供带空格路径的 `bash.exe`；CI 没有该 conf 时由 PATH 解析 `bash`。回退只解决脚本启动，不替代编译器、链接、目标执行或 W3 证据。

### 禁止做法

- 不要把缺失 conf 的返回值直接格式化进命令。
- 不要为了绕过 RC 127 删除 test_package 或把测试标记为 PASS。
- 不要用工作站绝对路径覆盖 CI 的 Bash 环境。

## 验证

```powershell
python -m py_compile archives/h/hamlib/4.7.2/test_package/conanfile.py
conan create archives/h/hamlib/4.7.2 --profile:host local-ohos.profile --build=missing
```

本轮本地回归 RC=0，日志中的 test package 命令为显式 `bash.exe` 路径，consumer 编译完成且没有 `None: inaccessible or not found`。平台 CI #44952 的失败日志绑定了该修复前的真实错误；修复后仍需新的当前 HEAD CI 终态。

## 适用范围与安全边界

适用于 Conan 交叉构建中由可选 conf 选择 shell/脚本解释器的 test_package。它不证明目标设备可登录、传输、签名或执行；配方、test_package 或 CI 修复改变后必须重新绑定当前 HEAD 的 CI 和 W3 证据。
