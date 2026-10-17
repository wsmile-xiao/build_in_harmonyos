# aetos 2.0.0 适配笔记

## 编译环境

- 构建系统: python（纯 Python 包，无编译）
- 编译日期: 2026-09-13
- 状态: built（配方已完成，待 HMBS 真机预检）
- 特殊说明: 纯 Python 包，无 .so、无 ELF 签名，不受 HMDFS/SELinux
  dlopen 限制；运行时重度依赖 OpenStack 生态，本轮诚实降级

## 库简介

aetos 是 OpenStack Telemetry 系的 Prometheus 反向代理，为每个
Prometheus 查询强制执行 OpenStack 多租户隔离与 Keystone 认证。

- 上游仓库: https://opendev.org/openstack/aetos
- PyPI: https://pypi.org/project/aetos/2.0.0/
- 许可证: Apache-2.0
- 类型: 纯 Python（pbr/setuptools，requires_python >= 3.10）
- 源码: aetos-2.0.0.tar.gz（42897 字节，
  sha256 2cde3107f95b22224bf17d811967f327205d913f2d5ac4578fb81c4fe361914f，
  已本地下载核验一致）

## Conan 配方说明

### 配方结构

- `conanfile.py`: python-require 配方（source 下载 + build() staging
  copytree + package() 拷贝 aetos/ 到 lib/python3.12/site-packages，
  附带 PKG-INFO/setup.cfg 快照与 etc/aetos/ 配置）
- `conandata.yml`: PyPI 官方源 + pypi.org 回退，同一 sha256
- `test_package/`: 消费者测试，真实 API 验证（见下）
- `manifest.yaml`: 版本级 manifest（built，待 CI upload 后转 published）
- `notes.md`: 本文件

### 关键配置

- `package_type = "python-require"`（纯 Python 库，不用 application，
  避免 R38 commands.json 门禁）
- `requires = []`（见依赖节 R36 审计）
- staging 用 `self.build_folder/aetos-stage`（源外目录，awscli WR-008
  教训：不用硬编码绝对路径，避免并发构建互相覆盖）
- `package()` 守护：staging 缺失、aetos/ 缺失、api-paste.ini 缺失均抛
  ConanException，拒绝产出残包

## 依赖

上游 PKG-INFO Requires-Dist 共 14 项：

pbr>=6.0.0、keystonemiddleware>=5.1.0、lxml>=2.3、oslo.config>=6.8.0、
oslo.i18n>=1.5.0、oslo.log>=4.3.0、oslo.policy>=4.5.0、PasteDeploy>=1.5.0、
Paste>=3.10、pecan>=0.8.0、oslo.middleware>=3.22.0、oslo.utils>=4.7.0、
WSME>=0.12.1、python-observabilityclient>=1.1.0。

仓库现状核验（archives/ 目录审计）：

- 仅 pbr/7.0.3 有配方目录（且无版本级 manifest，未发布），
  lxml/6.1.1 为 C 扩展包（非纯 Python 的 lxml 发行）；
- keystonemiddleware、pecan、Paste/PasteDeploy、WSME、oslo.*、
  python-observabilityclient 均无任何配方目录。
- 结论：14 项中 0 项可声明。按 R36 门禁，声明未发布依赖会直接
  失败 L0i，因此本轮 `requires = []`，缺失链如实记录，不静默丢弃。

运行时影响：除空 `aetos/__init__.py` 外，所有业务模块
（app/service/middleware/controllers/rbac/policies/opts/conf/defaults）
顶层即 import pecan/oslo_* /observabilityclient，缺依赖时
`import aetos.app` 必抛 ModuleNotFoundError。test_package 对此做
受控降级验证（见下），不伪造通过。

## 测试说明

### 上游测试（真机真实执行，pip 隔离补齐）

- 位置：aetos/tests/unit/test_base_controller.py（8 个 def test_）、
  aetos/tests/functional/test_admin_endpoints.py（9 个 def，含
  AdminEndpointsErrorCommonTests mixin×3 继承，pytest 执行 15）、
  aetos/tests/functional/test_core_endpoints.py（27 个 def，含
  CoreEndpointsErrorCommonTests mixin×6 继承，pytest 执行 39）；
  def 合计 44，pytest 实际收集 62（8+15+39）。
- 框架：官方 stestr（tox.ini），真机经 pytest 执行（兼容
  testtools/unittest TestCase，无需 stestr 服务端），命令
  `python3 -m pytest aetos/tests -v --tb=short -p no:cacheprovider`。
- 依赖补齐（低成本，R36 安全）：`test_package/run_upstream.py` 经
  `pip install --target ./aetos-upstream/deps --prefer-binary`
 （cwd 即 conan build_folder，可执行；TMPDIR 系 hmdfs noexec，
  lxml .so 在此 dlopen 报 Permission denied，故 deps 不放 TMPDIR；
  pip cache 仍走 $TMPDIR，pytest 另加 --basetemp workdir/basetemp
  避开只读 /tmp）隔离安装 14 项 Requires-Dist（含 lxml：middleware.py
  顶层必需，pip musl wheel 无 OHOS 自签名故安装后经
  binary-sign-tool -selfSign 逐个自签 .so（含版本化 .so.1，
  lxml 配方先例），并将 deps 下全部含 .so 目录经
  LD_LIBRARY_PATH 导出以修复 --target 下 $ORIGIN/.libs
  供应商库（如 bcrypt 捆绑 libgcc_s）加载路径）+
  stestr/testtools/oslotest/WebTest/fixtures/pytest，不声明 Conan
  requires，不污染系统 site；sdist 官方源下载 + sha256 校验后解包，
  cwd 即解包根（policy.yaml-test 与 api-paste.ini 相对路径如上游预期）。
- 真机修复 2026-09-13：oslo.utils 传递依赖 netifaces 无 musl wheel
  转源码构建，OHOS Python sysconfig 自带 -lintl 但工具链无
  libintl，ld.lld 报 unable to find library -lintl。run_upstream.py
  新增 workdir/fakelib 桩（优先复用系统 libintl，否则 clang 编译
  空 stub libintl.so/.a，LDFLAGS/LIBRARY_PATH 指向 fakelib，随
  pip env 透进 PEP517 构建），musl 下 gettext 本就在 libc，该
  flag 冗余，桩仅补链接、不删减任何测试。
- 防证伪：解包后断言 3 个测试文件非空；pytest 全量输出回显进日志；
  收集数为 0、退出码 0 但计数不一致、存在失败/跳过一律判 failed，
  绝不输出 skipped  stub；数字来自 pytest 真实解析。

### test_package 测试（消费者视角，R34）

- 文件：`test_package/test_aetos.py`（独立测试源，L0c），由
  `test_package/conanfile.py::test()` 经 `self.run()` 执行，
  失败即 conan create 失败。
- 5 项真实检查（非空壳）：
  1. `import aetos` 成功（包可被 PYTHONPATH 发现）；
  2. 包结构完整：controllers/api/v1/{base,query,series,labels,label,
     status,targets,root}.py、controllers/root.py、wsgi/api.py、
     app.py、service.py、middleware.py、policies.py、rbac.py、
     opts.py、api-paste.ini 全部存在；
  3. 元数据：PKG 快照含 `Version: 2.0.0`，Requires-Dist 计 14 项
     且含 pecan/oslo.config/python-observabilityclient 关键字；
  4. 配置解析：configparser 读取 api-paste.ini，断言
     `[composite:aetos+keystone]`、`[app:aetosv1]`、
     `paste.app_factory = aetos.app:app_factory`、
     `root = aetos.controllers.api.v1.root.V1Controller`；
  5. 重依赖受控降级：`import aetos.app` 预期抛 ModuleNotFoundError
     （缺 pecan/oslo），捕获并核验缺失模块名属已知 14 项之一；
     若意外导入成功或抛非 ImportError 则判失败（防静默跳过）。
- 机器证据：test() 先输出 `HMBS_TEST_PACKAGE_RESULT`
 （discovered=5/passedCount=5），再由 `run_upstream.py` 真实运行
  pytest 并输出 `HMBS_UPSTREAM_TEST_RESULT`（discovered=pytest
  收集数，executed/passed/failed/skipped 均来自解析，失败即
  conan create 失败）。

## 验证结果

- 本轮：配方工作树完成，未提交；待 HMBS 真机预检
  （conan create + test_package 5/5 + 上游审计标记）。
- 本地仅做源码包下载 + sha256 核验 + `def test_` 计数，
  未在本机运行 conan（按任务守则，验证转真机）。

## 注意事项

1. 单 PR 单库：本分支只含 archives/a/aetos/2.0.0/。
2. 不碰基础设施：未改 SKILL.md/references/templates/scripts/ci。
3. 中文 UTF-8 无 BOM；GitCode 写接口本轮禁用。
4. 后续若真机要求补依赖，按拓扑序先立项 oslo.* 等底层包，
   不在本 PR 捎带多包。

## 真机修复 2026-09-13（preflight upstream_test ResolutionImpossible）
- 现象：bulk-19 在镜像源报 oslo-config 全版本冲突、默认源报
  keystonemiddleware 全版本冲突；分相安装推进到 oslo.middleware>=3.22.0
  时双源均 ResolutionImpossible，run_upstream 以 failed 退出（62 用例未执行）。
- 根因：oslo.middleware 的传递依赖 bcrypt>=3.1.3 在镜像源仅提供
  cp312-ohos_aarch64 预编译 wheel（PEP 503 简单页实测 5 个 bcrypt ohos 包、
  lxml 5 个 ohos 包），标准 pip 标签集不含 ohos_aarch64，解析器过滤后
  可用版本为零，表现为全版本 conflicting dependencies；本地
  `pip install --dry-run --index-url <mirror> bcrypt` 复现
  `from versions: none`。默认源在受限真机网络下同样无法闭环。
- 修改（test_package/run_upstream.py，未提交待真机复验）：
  1. 修 AI Review P2：rank_lxml_wheel 的 abi 标签索引 parts[-4]（版本号）
     改为 parts[-2]，直接下载兜底路径才能命中 sys_tags。
  2. pip_install_list 新增 no_deps 参数；分相安装某包双源失败时以
     --no-deps 重试顶层安装（绕开传递闭包解析），记录 no_deps_pkgs。
  3. 新增 ohos_wheel_candidates/install_ohos_wheel_pkg：解析镜像源简单页，
     下载当前解释器标签（如 cp312）的 ohos_aarch64 wheel 并 zip 解包到
     deps_dir（绕开 pip 标签检查），.so 仍走既有 sign_so_tree 自签。
  4. oslo.middleware 走 --no-deps 时补齐传递闭包：bcrypt 走 ohos 解包
    （仅 cp312），oslo.context/stevedore/WebOb/Jinja2/statsd/debtcollector/
     six 走单包安装（with-deps 失败则 --no-deps 重试）。
  5. pip_install 开头打印 python 版本/pip 版本/tags 数量供下轮定位。
- readonly_tmp 平台诊断：preflight.sh 自身写 /tmp 失败属 infra 侧；
  本执行器早已避开 /tmp（workdir/deps 在 conan build_folder、
  PIP_CACHE_DIR 走任务 TMPDIR、pytest --basetemp 在 workdir），本轮未改测试口径。
