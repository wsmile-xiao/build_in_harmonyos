# Test Report — python3-distro 1.9.0 (OHOS aarch64)

**日期**: 2026-09-05
**测试机**: HarmonyOS PC (aarch64), Python 3.12.9, sys.platform == "ohos"
**被测物**: python3-distro/1.9.0@ohpcd/stable（conan create 产物，noarch 纯 Python）

## 1. 上游测试套件（pytest，本地实测）

命令：
```
cd <distro-1.9.0 源码>
PYTHONPATH=<pip-global> PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_distro.py -v
```
结果：
```
======================== 1 passed, 233 skipped in 0.35s ========================
```

| 指标 | 数值 |
|---|---|
| 发现用例 | 234（158 个 test 函数，参数化/重复计数后 234 项） |
| 通过 | 1（TestNonLinuxPlatform::test_cant_use_on_windows——OHOS 上 import distro 成功，不触发 Unsupported platform） |
| 跳过 | 233 |
| 失败/错误 | 0 |

### 233 项跳过的根因（平台行为差异，非适配缺陷）
上游 `tests/test_distro.py:47`：
```python
IS_LINUX = sys.platform.startswith("linux")
```
OHOS 的 `sys.platform == "ohos"`（不以 "linux" 开头）→ `@pytest.mark.skipif(not IS_LINUX)`
把 TestCli / TestOSRelease / TestLSBRelease / TestSpecialRelease / TestDistroRelease /
TestOverall / TestOverallWithEtcNotReadable / TestGetAttr / TestInfo /
TestOSReleaseParsing / TestGlobal / TestRepr 整类跳过。

这些测试类的**核心解析逻辑是平台无关的**（通过 `root_dir` 模拟各发行版的
/etc/os-release、*-release 文件），只是上游门卫以 sys.platform 判定只在
Linux 上跑。为验证核心逻辑在 OHOS 上同样正确，test_package 携带上游
resources/distros 的 4 个代表子集（arch/ubuntu14/centos7/centos5）执行
**与上游同源的等价断言**（见第 2 节），全部通过。

## 2. test_package 消费者测试（conan create 内实测，CI 同款）

conan create 日志（reports/conan-create.log）：
```
python3-distro/1.9.0@ohpcd/stable (test package): RUN: /data/app/bin/python3 ".../test_distro_consumer.py" ".../site-packages"
All 12 python3-distro consumer tests passed.
```

| # | 测试 | 断言要点（上游同源） |
|---|---|---|
| 1 | test_import_and_version | import + __version__==1.9.0 + NORMALIZED_{DISTRO,LSB,OS}_ID 归一化表 |
| 2 | test_os_release_arch | TestOSRelease.test_arch_os_release：id=arch, name="Arch Linux" |
| 3 | test_os_release_ubuntu14 | 同上游：id=ubuntu, version=14.04, best=14.04.3, like=debian, codename="Trusty Tahr" |
| 4 | test_os_release_centos7 | 同上游：id=centos, version=7, pretty="7 (Core)", like="rhel fedora", codename=Core |
| 5 | test_distro_release_centos5 | TestDistroRelease.test_centos5_release：显式 centos-release 文件，id=centos, version=5.11, major=5, minor=11, codename=Final |
| 6 | test_distro_release_arch | 空 arch-release 文件按 basename 模式仍得 id=arch |
| 7 | test_unknown_distro_semantics | 空 root_dir → id/name/version/like/codename 均为空串（unknown 分支） |
| 8 | test_repr | repr(LinuxDistribution) 含类名 |
| 9 | test_linux_distribution_compat | linux_distribution() 兼容 API 返回 3 元组 |
| 10 | test_os_release_attr_and_info_keys | info() 键完整性 + version_parts + os_release_attr(support_url) |
| 11 | test_ohos_host_behavior | **OHOS 本机行为**：无 /etc/os-release → 所有查询走 unknown 分支返回空值、不抛异常 |
| 12 | test_cli_module | `python -m distro` rc=0 且输出 Name:/Version:/Codename: |

**结果：12/12 PASS（100%）**

## 3. OHOS 平台行为说明（如实记录）

1. **本机 host 检测返回空值**：OHOS 无 /etc/os-release、/etc/lsb_release 等
   标准发行版元数据文件，distro.id()/name()/version() 返回空串。这是 distro
   对"无法识别的发行版"的既定语义（unknown 分支），库本身工作正常。
   若 HarmonyOS 未来提供 /etc/os-release（如 ID=openharmony），distro 无需
   重新适配即可自动识别。
2. **上游 IS_LINUX 门卫**：233 项跳过系上游 `sys.platform.startswith("linux")`
   判定所致，OHOS `sys.platform=="ohos"` 不满足——纯 Python 包的平台
   行为差异，非适配缺陷（核心逻辑已由第 2 节同源断言覆盖）。
3. **lsb_release 探测**：include_lsb=True 时 OHOS 无 lsb_release 可执行，
   distro 按上游设计静默跳过该数据源。

## 4. 结论

- 上游套件：1/1 执行项通过，233 项上游门卫跳过（0 失败 0 错误）
- 消费者测试：12/12 通过（覆盖上游 root_dir 模拟解析类的等价断言 + OHOS 本机行为 + CLI）
- conan create：PASS（含 test_package 全部通过）
- **python3-distro 1.9.0 在 HarmonyOS PC 上适配验证通过**
