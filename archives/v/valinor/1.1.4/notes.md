# valinor 1.1.4 适配笔记

## 上游
- ARMmbed/valinor 1.1.4, PyPI sdist valinor-1.1.4.tar.gz (sha256 3461ba5d0c112a6efecfc774d7d1fd612eaf5c3609dbe0eb18f0acaf4d861384)
- 纯 Python noarch，无编译；valinor/ 拷贝到 site-packages，运行/测试依赖 pip --target 隔离安装 (pyelftools==0.23, project_generator==0.8.4, colorama, nose, setuptools<81+wheel bootstrap 经 PYTHONPATH 暴露给 --no-build-isolation)
- project_generator 0.8.x 全系 sdist 且 setup.py 在现代 pip 下必败：`from pip.req import parse_requirements` + `pip.download.PipSession()` (pip 10 已删除)，报错 `Preparing metadata ... ModuleNotFoundError: No module named 'pip.req'` (本地 pip 26 复现出与真机逐字相同的 metadata-generation-failed)。任何 pip flag 都绕不过，只能下载 sdist → 改写 setup.py (直读 requirements.txt，跳过 argparse backport) → 本地目录 pip install。固定 0.8.4 (valinor 允许范围顶部)。
- OHOS/Python3.12+ 适配 (build() 内 replace_in_file，精确匹配，漂移即loud失败)：ide_detection.py 的 distutils.spawn → try/except 回退 shutil.which；`import _winreg` (py2专有) → try winreg；main.py 的 `pkg_resources.require("valinor")` (staging 无 egg-info 且 pyOCD 缺席，require 必抛 DistributionNotFound 导致每次 CLI exit 1) → 惰性 helper + "1.1.4" 回退。
- staged 依赖补丁：pyelftools 0.23 内嵌 construct 的 `from collections import MutableMapping` (3.10 已删) → collections.abc 回退；project_generator_definitions≤0.2.9 的无 Loader yaml.load → FullLoader (0.2.46+ 已自带，仅旧版命中)。
- setuptools<81：81+ 删除了 pkg_resources (main.py 仍 import)。本地探针确认各版本：pyYAML 6.0.3 / Jinja2 3.1.6 / xmltodict 1.0.4 / pg_definitions 0.2.46 / nose 1.3.7 / setuptools 80.9.0 (pytest 已删：runner/test_package 均未使用)。
- OHOS 适配: build() 用 replace_in_file 将 ide_detection.py 的 distutils.spawn → try/except 回退到 shutil.which (Python 3.12 distutils 已删除)
  (不用 context-diff 补丁文件避免 hunk 头/fuzz 在真机 patch 工具下被拒)

## 上游测试 (3 个)
- valinor/test/test_outputdir.py: 2 个 TestCase 方法，真实 CLI -n 生成 .uvproj/.gdbstartup 并断言文件存在
- valinor/test/test_exporter.py: 1 个 nose 函数，断言通用 Builder.build_project 抛 NotImplementedError
- build() 用 unittest result 对象计数 (testsRun/failures/errors/skipped + 手动运行 exporter)，不做 stdout 字符串数数；标识式自检后持久化到 res/upstream_test_result.json
- exporter 语义：nose @raises 装饰器吞掉预期的 NotImplementedError 后正常返回＝通过 (旧逻辑倒置)；Python≥3.12 nose 因 `imp` 被删无法 import，runner 回退到对同一 Builder.build_project 的直接断言并打印 exporter=direct_builder/nose_decorator 供日志取证
- 证伪：本地探针已验证 .uvproj (12KB 真实 XML 含 K64F、无 b'' 字节残留) 与 .gdbstartup (32B `target remote`) 均为真实生成，非空文件比对

## test_package (5 个)
- test_valinor.py: import + main 可调用 + 非 ELF 返回 [] + gdb 工厂可调用 + logging init，计数器直接产生 HMBS_TEST_PACKAGE_RESULT

## 验证
- conan create archives/v/valinor/1.1.4 --build=missing
- 预期上游 3/3，消费者 5/5；以真机预检日志为准
- Signal 9 削峰：pip 多包单次安装改为逐包串行 + pip_env 禁缓存/版本检查，不改测试口径。

- 真机 2026-09-30 compile 失败：修复后 project_generator 本地树 pip install 在解析 pyYAML 时报 from versions: none / No matching distribution found for pyYAML。直接证据为预检 stderr 尾部。根因为 pip 被固定到内部 subset 镜像（cnb.cool），该镜像无 pyYAML；单次 pip install 只用首个 index，不会自动回退。修复：pip 安装改为有序 index 回退（内部镜像→tuna→aliyun→pypi.org，带 retries/timeout），project_generator 本体先 --no-deps 安装再逐个显式安装 pyYAML/Jinja2/xmltodict/project_generator_definitions，bootstrap 与 pyelftools/colorama/nose 同理走回退。

- 真机 2026-09-30 test_package 4/5：FAIL valinor.main callable，`from valinor import main` 拿到的是函数本身（__init__.py 做 from .main import main），旧断言 main_mod.main 必然失败。修复：测试接受函数直调或模块.main 两种形态，不删断言不改口径。
