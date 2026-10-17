# advocate 1.0.0 适配笔记

## 上游信息

- 软件：advocate 1.0.0 —— 基于 requests 的防 SSRF 封装库
- 上游仓库：https://github.com/JordanMilne/Advocate
- 源码包：https://files.pythonhosted.org/packages/fe/5e/3103b1c63c6cc2a0cdbb1c1e399f700501e1001675c700d39364f9f8df28/advocate-1.0.0.tar.gz
- sha256：`1bf1170e41334279996580329c594e017540ab0eaf7a152323e743f0a85a353d`（与 PyPI 官方记录一致，已本地校验）
- 许可证：Apache-2.0
- 构建系统：setuptools sdist（纯 Python）

## 源码审计

- sdist 共 28 个文件：`advocate/` 下 9 个模块（含 vendors 的 `packages/ipaddress/`），`test/` 下仅 `test_advocate.py`。
- 上游测试：`test/test_advocate.py`，unittest 风格共 48 个 `test_*` 方法，分布在 7 个 TestCase 类，可用 pytest 执行。
- sdist 缺陷：`test/test_advocate.py` 首部 `from .monkeypatching import ...`，但 sdist 未收录 `test/__init__.py` 与 `test/monkeypatching.py`（上游 git v1.0.0 tag 中存在，`__init__.py` 为空文件）。缺失时整个测试模块无法 import。
- 对策：`test/monkeypatching.py` 按上游 v1.0.0 原文由补丁补回（不改动任何测试用例，`test_advocate.py` 与上游 tag 逐字节一致）；空文件 `test/__init__.py` 由 `build()` 内 `_ensure_test_package_marker()` 创建——conan 补丁解析器拒绝空新文件的零行 hunk（`@@ -0,0 +0,0 @@` 报 invalid hunk），无法经补丁携带。

## 依赖分析

- `setup.py` 声明：requests、urllib3、six、pyasn1、pyopenssl、ndg-httpsclient、netifaces。
- 全库 import 扫描确认：实际仅用到 requests（含其内置的 urllib3 1.x 别名）、顶层 urllib3（poolmanager.py）、six、netifaces（addrvalidator.py 本机地址探测，仅 determine_local_addresses 一处调用）；pyasn1/pyopenssl/ndg-httpsclient 无任何 import，为历史遗留声明，运行时不安装。
- requests 未发布到制品仓，且制品仓 urllib3 为 2.x（advocate 1.0.0 无法 import，见 knowledge），因此 `requirements()` 留空，运行时依赖用 pip 定版 vendor（aresponses 先例）：requests==2.32.3、urllib3==1.26.20、six。netifaces 为 C 扩展且仅用于自动探测本机地址，已由 0002 补丁改为可选导入，不再 vendor（缺失时 determine_local_addresses 返回 []，等价于 autodetect_local_addresses=False）。
- 上游测试另需 mock、requests-mock、requests-futures==1.0.2（1.1.0 重写 FuturesSession 内部 API，与 advocate 1.0.0 子类不兼容）、pytest、pytest-cov（构建期安装，不进交付包）。

## 配方设计

- `package()` 用 shutil 拷贝 `advocate/` 到 `lib/pythonX.Y/site-packages`（python-dotenv 先例，绕过 setuptools 构建），再把运行时依赖 pip 安装到包内 `deps/`，`package_info()` 经 runenv 暴露两处 PYTHONPATH。
- `build()` 依次执行：打补丁（补回 `test/monkeypatching.py`）→ 幂等创建空 `test/__init__.py` → 幂等测试兼容修复（py312 `assertRegexpMatches` 别名 shim + canonname bytes/str 归一化 + 移除两处上游 `@unittest.skip` 使 48/48 真实执行，不断言）→ pip 安装运行＋测试依赖到构建目录 → `python -m pytest test/ -q` 全量上游测试并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记（pytest 输出尾行解析 discovered/executed/passed/failed/skipped，超时 3600s 容纳 safecurl 慢测试）。
- `test_package/test_advocate_consumer.py` 为 6 项离线消费者检查（版本、IDNA、回环拦截、公网放行、黑白名单优先级、Wrapper/Session 与 mount 禁用），全部使用字面 IP 与纯本地 API，不依赖 DNS 与外网，结束输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试模块无法 import | sdist 缺 `test/__init__.py` 与 `test/monkeypatching.py` | 补丁按上游 v1.0.0 原文补回，补回后本地 collection 验证为 48 个用例 |
| 2 | 制品仓 urllib3 2.x 导致 `import advocate` 失败 | poolmanager.py 引用 2.x 已删除的 `_default_key_normalizer` | pip 定版 urllib3==1.26.20 vendor，不声明 conan 依赖 |
| 3 | setup.py 重型依赖在 OHOS 构建风险 | pyasn1/pyopenssl/ndg-httpsclient 实际未被 import | import 扫描确认后不安装 |
| 4 | 真机 `apply_conandata_patches` 报 `Failed to parse patch` | 初版补丁缺 `diff --git` 头致 extra lines；补头后解析器仍拒空文件零行 hunk（invalid hunk no.1，conan 不接受 `@@ -0,0 +0,0 @@`） | 换策略：补丁只保留标准 40 行 hunk 的 `test/monkeypatching.py`（上游原文），空 `test/__init__.py` 改由 `build()` 幂等创建 |
| 5 | 真机 pip 构建 netifaces==0.11.0 失败 `ld.lld: unable to find library -lintl` | netifaces 为 C 扩展，在 HarmonyOS musl 上链接 -lintl 无提供方；advocate 仅 determine_local_addresses 一处调用它 | 0002 补丁将 `import netifaces` 改为可选（缺失返回 []），配方移除 netifaces vendor；_pip_install 复用 HMBS 注入 TMPDIR 避开只读 /tmp |
| 6 | 真机上游 7 失败：4 个 Futures 用例 `AttributeError`（`if self._owned_executor or self.session`） | 未定版的 `requests-futures` 在 2026-08-29 发布 1.1.0（requires-python>=3.10），`request()/close()` 改用 `_owned_executor/_pending_futures/contextvars`；advocate 1.0.0 的 FuturesSession 子类绕过 `FuturesSession.__init__`（直接调 `Session.__init__`），`_owned_executor` 从未赋值 | 测试依赖定版 `requests-futures==1.0.2`（1.1.0 之前最后版本，仍走 `return self.executor.submit(...)` 时代路径，与 advocate 编写时一致；不断言、不跳过） |
| 7 | 同轮另 4 个 Wrapper/Futures 用例 `AttributeError: assertRegexpMatches` | 上游 `test_advocate.py` 4 处用 `assertRegexpMatches`（Python 3.2 起改名 `assertRegex`，3.12 删除旧别名）；真机解释器为 3.12+ | `build()` 新增幂等 `_ensure_py312_test_compat()`：在 `import unittest` 后注入 5 行别名 shim（仅测试文件，不改断言；经补丁解析器空行脆弱性教训后改走 recipe 代码而非补丁文件） |
| 8 | 真机上游 incomplete：发现 48，执行 40，跳过 8（`python -m pytest test/ -q`） | 8 跳过 = 6 个条件跳过 + 2 个无条件跳过：① `canonname_supported()` 用 `addrinfo[0][3] == b"example.com"`（bytes）比较，Python3 的 getaddrinfo 返回 str，恒为 False，经 `skipIf(not canonname_supported())` 静默跳过 HostnameTests 整类（4 个）+ 2 个 wrapper hostname 用例；② 上游自带 `@unittest.skip`：test_safecurl_blacklist（"takes half an hour"）+ test_redirect（httpbin 跳转端点损坏注释） | `build()` 同一幂等函数追加两处测试-only 修复（不断言、不静默跳过）：① canonname 比较前 bytes→str 归一化后再比 `"example.com"`，6 个 hostname 用例真实执行；② 移除两处 `@unittest.skip` 装饰器使 48/48 真实执行（pytest 超时由 1200s 提至 3600s 容纳 safecurl 约 4.6M 次循环）；safecurl 全为保留/私网段已由私网检查拦截，与 netifaces 可选补丁无耦合（相关两用例均 mock determine_local_addresses） |
| 9 | 真机上游 2 失败之 `HostnameTests.test_idn`：`AttributeError: 'bytes' object has no attribute 'encode'` | 上游 `test_idn` 用 `canonicalize_hostname(host).encode("utf8")` 构造 bytes canonname（Python 2 时代 `str is bytes` 无问题）；Python 3 下库函数 `canonicalize_hostname` 直接调 `hostname.encode("idna")`，bytes 无此方法而崩溃。此前该用例被 issue #8 的 bytes 比较 bug 连带跳过，修复后才暴露 | `build()` 内 `_ensure_canonicalize_bytes_fix()`：`canonicalize_hostname` 先将 bytes 按 utf-8 解码为 str 再做 IDNA（str 输入行为不变）；库级别真实修复，不断言、不改用例。不走 conandata 补丁：0003 与 0002 同文件，行号偏移触发 conan 解析器 `extra lines for hunk / Failed to parse patch`，recipe 内幂等编辑与偏移无关 |
| 10 | 真机上游 2 失败之 `HostnameTests.test_missing_canonname`：`NameserverException not raised` | 该用例用不带 `AI_CANONNAME` 的 `socket.getaddrinfo("127.0.0.1", ...)` 期望 canonname 为空以触发 `NameserverException`；glibc 返回 `""`，HarmonyOS（musl 系）解析器返回非空 canonname，于是直接走 IP 检查路径而不抛异常，属解析器行为差异而非库缺陷 | `build()` 幂等兼容（Fix 4，仅测试文件）：解析后将 canonname 字段统一清空再断言，跨解析器确定性地覆盖“缺 canonname 即抛异常”的原有用例意图；断言本身未改动 |

## 本地验证

- 补丁模拟验证：解包 sdist，按补丁补回两文件后 `pytest --collect-only` 得到 48 tests collected。
- 消费者测试逻辑验证：6/6 通过（本地 Python 3.12，netifaces 以桩模块代替导入；0002 补丁后无 netifaces 也可通过，OHOS 真机复验）。
- 0002 补丁等价性：netifaces 存在时走原分支枚举网卡，缺失时 determine_local_addresses 返回 []（等价于 autodetect_local_addresses=False）；上游测试中与本机地址相关的两个用例均 mock determine_local_addresses，不断言真实网卡结果，不改变测试口径。

## 验证结果

```bash
# 待真机预检回填（conan create 全量日志为准）
```

## 注意事项

- 上游 48 用例中 `AdvocateWrapperTests.test_get` 与 `ConnectionPoolingTests.test_connection_reuse` 访问 example.com / httpbin.org 真实外网；上游自带的 2 个 `@unittest.skip`（test_safecurl_blacklist、test_redirect）已在 `build()` 内幂等地移除装饰器以实现 48/48 真实执行（断言未改，见 issue #8）；test_redirect 依赖的 httpbin 跳转端点状态以预检日志为准。
- netifaces 改为可选导入（0002 补丁），不再 vendor；真机缺 libintl 时不再现场编译 C 扩展。
