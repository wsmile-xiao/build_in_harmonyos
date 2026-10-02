# DRAFT: pip install --prefix 跳过构建机已装依赖，python-require 包不自包含

- **条目主题**：纯 Python 包做 conan `python-require` 包时，`pip install . --prefix=<stage>`
  因构建机宿主已装同名依赖而**漏装依赖闭包**，产出包不自包含（本地假绿、消费机 ModuleNotFoundError）。
- **状态**：草稿（待知识库主编审核，拟提升编号 Exxx）
- **关联**：rapt-ble 0.1.2 适配（archives/r/rapt-ble/0.1.2，PR 待提）
- **同型/相邻条目**：E512（宿主预装致本地绿、CI 干净环境红 —— 本条是其打包侧成因与修复）、
  DRAFT-VENDP-PUREPY-DEP-CLOSURE（无配方运行依赖的 vendor 方案，本案例走 pip 镜像闭包路径）

## 适用场景

以 `pip install <src> --prefix=<stage>` 生成 conan 包内容的纯 Python 配方
（`package_type = "python-require"`、`layout()` 用 `basic_layout`、`package()` 整前缀拷贝）。
典型信号：

- 本地 `conan create` 通过、test_package 通过，但**干净机器**上 `import <pkg>` 报
  `ModuleNotFoundError: No module named 'cryptography'`（或 cffi / pycparser 等）。
- `pip install` 日志出现 `Requirement already satisfied: cryptography ... in
  /usr/local/lib/python3.12/site-packages`（写的是**宿主路径**，不是 `--prefix` 目标）。
- 包内 site-packages 里恰好"少了构建机装过的那几个包"。

## 诊断步骤

1. 造两级前缀对比（构建机保留宿主预装，不做任何清理）：

   ```bash
   python3 -m pip install <src> --prefix=$HOME/tmp/stage-a --no-warn-script-location
   python3 -m pip install <src> --prefix=$HOME/tmp/stage-b --ignore-installed --no-warn-script-location
   comm -13 <(ls $HOME/tmp/stage-a/lib/python3.12/site-packages|sort) \
            <(ls $HOME/tmp/stage-b/lib/python3.12/site-packages|sort)
   ```

   差值即"被 already satisfied 判定吃掉"的依赖。
2. 用干净 venv（默认不带 system-site-packages）模拟消费机，只把 staging 前缀塞进 PYTHONPATH：

   ```bash
   python3 -m venv $HOME/tmp/venv-clean
   PYTHONPATH=$HOME/tmp/stage-a/lib/python3.12/site-packages \
       $HOME/tmp/venv-clean/bin/python -c "import <top-level-dep-import>"
   ```

   报 ModuleNotFoundError 即证伪"自包含"。
3. 修复后再跑一次第 2 步，期望打印 OK（本案例
   `import bluetooth_data_tools, cryptography, cffi` → `OK self-contained`）。

## 真实证据（rapt-ble 0.1.2）

| 步骤 | 命令 | 结果 |
| --- | --- | --- |
| 无 `--ignore-installed` | `pip install <src> --prefix=$HOME/tmp/stage-noignore` | 前缀 32 项；日志 `Requirement already satisfied: cffi.../cryptography.../pycparser... in /usr/local/lib/python3.12/site-packages` |
| 有 `--ignore-installed` | `pip install <src> --prefix=$HOME/tmp/stage-ignore --ignore-installed` | 前缀 39 项（全闭包） |
| 差集 | `comm -13` | `cffi`、`cryptography`、`pycparser`、`_cffi_backend.cpython-312-aarch64-linux-ohos.so` |
| 干净 venv + 无 ignore 前缀 | `PYTHONPATH=...stage-noignore/... venv/bin/python -c "import bluetooth_data_tools"` | `ModuleNotFoundError: No module named 'cryptography'`（栈顶 `bluetooth_data_tools/privacy.py:16 from cryptography.hazmat.primitives.ciphers import ...`） |
| 干净 venv + 有 ignore 前缀 | 同上指向 stage-ignore | `OK self-contained` |
| 最终 conan 包 | `conan create archives/r/rapt-ble/0.1.2 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` | 消费者断言 27/27 + 上游 pytest 7/7 |

> 注意 OHOS 差异：镜像提供的 `cffi` 是 **OHOS aarch64 原生 wheel**
> （`_cffi_backend.cpython-312-aarch64-linux-ohos.so`），漏装后不仅"缺模块"，
> 补装时也必须走同一镜像才拿到 OHOS 版 ABI，不能用宿主 Linux wheel 顶替。

## 修复

```python
# conanfile.py build()
self.run(f"{python} -m pip install . --prefix={stage} "
         f"--ignore-installed --no-warn-script-location", env="conanbuild")
```

- `--ignore-installed`：绕开基于**宿主 sys.path** 的"已满足"判定，强制把整棵依赖闭包
  重新解析进 `--prefix` 目标。
- `--no-warn-script-location`：纯路径告警抑制（不影响产物）。

## 验收判据（不要用"本地 conan create 绿"当判据）

必须在**干净 venv**（`python3 -m venv`，默认不继承 system-site-packages）里，
只用包内 site-packages（PYTHONPATH）完成一次真实 import——本机宿主预装会让
本地测试假绿（E512 同型）。

## 推广价值

- 所有 `python-require` / pip-staging 型纯 Python 配方；尤其依赖树含 C 扩展
  （cffi/cryptography/pycparser、yarl/markupsafe 等）时，宿主预装概率高、漏装更隐蔽。
- 可提炼为通用检查项：**"staging 前缀条目数 vs 干净环境 import"** 双判据。

## 查重关键词

`--ignore-installed`、`--prefix`、`Requirement already satisfied`、宿主 site-packages、
staging 前缀、自包含、python-require、basic_layout、runenv_info、PYTHONPATH、
ModuleNotFoundError、cryptography、cffi、pycparser、bluetooth-data-tools、
本地绿远端红（E512 同型）
