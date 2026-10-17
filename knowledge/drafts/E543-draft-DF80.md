# E543 — OHOS Python C 扩展的 Conan ABI、加载权限与测试环境闭环

## 错误特征
典型症状包括：编译器找不到（`command 'cc' failed: No such file or directory`）、Python 头文件缺失、扩展导入时报 `undefined symbol`/`PyInit_* not found`、HMDFS 加载扩展时报 `Permission denied`、pytest 临时目录报 `temporary directory ... is not owned`，以及 Conan Python 的 `_ssl` 不可用导致 pip 无法获取测试工具。

## 触发条件
- 构建系统：setuptools 或直接 C 编译的 Python C extension
- 阶段：compilation/linking/packaging/runtime/testing

## 根因分析
OHOS 设备的 Python 解释器、头文件、libpython、编译器和二进制签名工具可能分布在不同环境。将某台设备的绝对路径固化到 Conan 配方会破坏干净 CI 和其他设备的复现；扩展即使编译成功，也可能因 ABI 不一致、未签名/不可执行权限或测试临时目录所有权而无法加载或运行。Conan Python 还可能没有可用的 TLS `_ssl`，因此不能假设 `python -m pip` 能访问 PyPI。

## 解决方案
### 推荐方案
将匹配的 `python/3.12.9` 作为 Conan 依赖；从依赖包动态发现 `Python.h`、`libpython*.so` 和 Python site-packages。编译器从 `tools.build:compiler_executables` 或 PATH 发现，签名工具从 OHOS 构建环境 PATH 发现。最终 package 阶段签名扩展并恢复 0755 权限，`package_info()` 通过 `runenv_info` 暴露 Python 路径。

test_package 使用同一 Conan Python 解释器。若测试镜像没有 pytest，使用 Conan Python 自带 `ensurepip`，由可用的 HTTPS 下载工具获取官方固定版本及其依赖 wheel，逐个校验 PyPI 返回的 SHA-256 后安装到一次性 test-only 目录，再用 `--no-index` 离线运行完整上游 suite。pytest 临时目录从环境候选中动态创建并执行写探针，再作为显式 `--basetemp` 传入；这避免 HMDFS 挂载所有权元数据与活动 UID 不一致时 pytest 拒绝共享根目录，测试结束后清理该目录。

### 禁止做法
- ❌ 将 `/data/service/...`、`/data/storage/...` 等设备私有路径写死到配方或知识方案。
- ❌ 混用系统 Python 头文件与另一套 libpython，或只依赖 ambient `python3` 而不验证解释器来源。
- ❌ 在全局 Python 中安装 pytest，或在没有 hash 校验的情况下把下载包当作可复现测试依赖。
- ❌ 用修改/跳过上游测试掩盖扩展加载权限、ABI 或临时目录问题。

## 验证
```sh
conan create archives/f/fastconstmap/0.9.0 \
  --build=fastconstmap/* \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -s:h os.version=6.0 -s:b os.version=6.0
```

最终设备日志应逐项给出 `TOTAL = PASS + FAIL + SKIP + NOT_RUN`，并同时证明扩展动态加载、签名权限、完整上游测试和消费者 smoke test。若测试工具缺失或网络/TLS 不可用，必须记录工具探测和第一条错误，不能把未运行写成 PASS。

## 实证记录
官方 CI #39300 证明仅依赖设备 ambient pytest 不可复现：CI 环境无 pytest。设备上的 Conan Python `_ssl` 也无法加载，因此直接 pip HTTPS 安装失败；改用系统 `curl` 下载官方 wheel、SHA-256 校验、私有离线 pip target 后，测试工具闭环恢复。后续 CI #39332 又证明 HMDFS 挂载的目录所有权元数据可能与活动 UID 不一致；动态创建目录、写探针并显式传 `--basetemp` 可避开 pytest 的共享根目录检查。#39353 在测试开始前的 G0e 阶段发现 CI checkout 根目录存在最终 SHA 未跟踪的 `test_file.txt`，本地 `git ls-tree -r HEAD` 未发现该文件，因此属于 CI 工作区污染而非配方问题；已再次触发 `/rebuild`。完整 suite 在设备上通过 56/56，消费者通过 2/2。

## 关联条目
- 相关：E004、E019、E022
- 来源 PR：!8218
- 来源提交：`ab9b31fc79dd700202cc7e9361093e27d3bc1f95`
