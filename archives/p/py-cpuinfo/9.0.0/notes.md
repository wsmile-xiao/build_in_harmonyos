# py-cpuinfo 9.0.0 适配笔记

## 上游信息
- **仓库**: https://github.com/workhorsy/py-cpuinfo
- **版本**: 9.0.0 (2022-05-14 release)
- **语言**: Pure Python 3
- **构建系统**: setuptools
- **许可**: MIT

## 构建方式
纯 Python noarch 包，无需 C/C++ 编译：
```bash
pip install --no-deps --prefix=<staging> <src_dir>
```

## 上游测试
上游提供完整测试套件 `tests/` 目录，159 个单元测试：
- setup.py 声明 `test_suite="test_suite"`
- test_suite.py 作为入口，加载所有 tests/*.py 模块
- 覆盖 7 大平台（Linux x86_64/ARM、BSD、macOS、Windows、Solaris、BeOS）

执行方式：
```bash
cd <source_folder>
python3 -m unittest test_suite -v
```

HarmonyOS aarch64 实测结果：
- **158 passed** + **1 skipped** (test_hz_actual_multiprocessing，ARM 平台预期行为)
- 1 failed → 打补丁后通过（见下文）

## HarmonyOS 平台兼容
### 问题
test_actual.py::TestActual::test_all 失败：
```
AssertionError: Unexpected OS type "Unknown".
```

### 根因
HarmonyOS 返回 `platform.system() == "HarmonyOS"`，
但上游 tests/helpers.py::get_os_type() 只识别 linux/darwin/windows 等，
未覆盖 harmonyos，导致映射到 'Unknown' 走 else 分支抛异常。

### 解决方案
补丁 `0001-ohos-platform-compat.patch`：
在 tests/helpers.py::get_os_type() 增加 2 行：
```python
elif 'harmonyos' in uname:
    os_type = 'Linux'
```

HarmonyOS 与 Linux 系统调用兼容（有 /proc/cpuinfo、lscpu），
test_actual.py 的 Linux 断言路径（检查 _get_cpu_info_from_proc_cpuinfo() 等）
在 OHOS 上同样成立，无需单独分支。

打补丁后上游 159 个测试全部执行，无删减：
- **159 tests** executed
- **158 passed** + **1 skipped** (ARM 预期行为)
- **0 failed**

## 补充消费者测试
test_package/test_cpuinfo.py 验证 Conan 打包正确性（4 项）：
1. import cpuinfo 模块
2. 调用 get_cpu_info() API
3. 检查返回字典包含必需键（arch/bits/count/brand_raw）
4. 运行 CLI `cpuinfo` 并验证输出

## 知识沉淀
- py-cpuinfo 为纯 Python 包，构建用 pip --no-deps 安装到私有 staging
- 提供 console_scripts entry point `cpuinfo`（在 bin/ 目录）
- HarmonyOS 平台识别需在测试辅助函数中补充，映射到 Linux 分支即可
- 上游测试套件完整（159 tests），适配补丁仅修改 1 个辅助文件 2 行，
  保留全部上游测试不删减
