#!/usr/bin/env python3
"""Consumer test for python3-distro 1.9.0 — core parsing + CLI smoke test.

上游 test_distro.py 的 root_dir 模拟解析类（TestOSRelease / TestDistroRelease /
TestOverall 等）平台无关——通过 resources/distros/ 模拟各发行版的
/etc/os-release、*-release 文件验证解析逻辑。本测试脚本将上游
resources 的代表性子集随包携带，在 OHOS 上执行同源断言：
  1. import + 版本 + NORMALIZED_* 归一化表
  2. TestOSRelease 等价断言：arch/ubuntu14/centos7 的 id/name/version/like/codename
  3. TestDistroRelease 等价断言：centos5（显式 distro_release_file）
  4. unknown 发行版语义：空 root_dir 返回空串（id()="" 等）
  5. best_version 语义：ubuntu14 的 14.04.3
  6. repr + linux_distribution() 兼容 API
  7. OHOS 本机行为：本机 /etc/os-release 缺失时 distro.* 返回空值
     ——纯 Python 包的平台行为差异（上游 IS_LINUX 门卫同因），如实断言
  8. CLI 入口：python -m distro 可执行且退出码 0

注意：脚本通过首参（被测包 site-packages 路径）把被测 distro 置于
sys.path 最前——防系统/用户环境已装同名 distro 干扰（本机 pip-global
即装有一份 distro 1.9.0）。
"""
import os
import subprocess
import sys
import tempfile

# 被测包 site-packages 优先（argv[1]，由 test_package/conanfile.py 传入）。
# 必须真实存在且被测 distro 从该路径加载——本机环境（pip-global 等）可能
# 已装同名 distro，仅 sys.path.insert 无法证明测试依赖被测包（R34/L1e：
# 破坏性反向验证移走产物后，若从别处兜底 import 成功即判假测试）。
SITE_ARG = sys.argv[1] if len(sys.argv) > 1 else ""
if not SITE_ARG or not os.path.isdir(SITE_ARG):
    print(
        f"FATAL: tested package site-packages missing or not a dir: "
        f"{SITE_ARG!r} — cannot verify the package under test",
        file=sys.stderr,
    )
    sys.exit(2)
sys.path.insert(0, SITE_ARG)

import distro as _distro_under_test  # noqa: E402

if not os.path.realpath(_distro_under_test.__file__).startswith(
    os.path.realpath(SITE_ARG)
):
    print(
        f"FATAL: distro loaded from {_distro_under_test.__file__}, "
        f"expected under {SITE_ARG} — test must depend on the packaged copy",
        file=sys.stderr,
    )
    sys.exit(2)

BASE = os.path.abspath(os.path.dirname(__file__))
RESOURCES = os.path.join(BASE, "resources")


def test_import_and_version():
    import distro

    assert distro.__version__ == "1.9.0", (
        f"version mismatch: {distro.__version__}"
    )
    from distro.distro import (
        NORMALIZED_DISTRO_ID,
        NORMALIZED_LSB_ID,
        NORMALIZED_OS_ID,
    )

    assert NORMALIZED_DISTRO_ID == {"redhat": "rhel"}, (
        f"NORMALIZED_DISTRO_ID: {NORMALIZED_DISTRO_ID}"
    )
    assert "enterpriseenterpriseserver" in NORMALIZED_LSB_ID, (
        f"NORMALIZED_LSB_ID: {NORMALIZED_LSB_ID}"
    )
    assert NORMALIZED_OS_ID["opensuse-leap"] == "opensuse", (
        f"NORMALIZED_OS_ID: {NORMALIZED_OS_ID}"
    )
    print(f"PASS: distro {distro.__version__} imported at {distro.__file__}")
    print("PASS: NORMALIZED_DISTRO_ID/LSB_ID/OS_ID normalization tables present")


def _make_os_release(root):
    """上游 TestOSRelease.setup_method 等价构造。"""
    from distro.distro import LinuxDistribution

    return LinuxDistribution(
        include_lsb=False,
        distro_release_file="path-to-non-existing-file",
        root_dir=root,
    )


def _make_distro_release(release_file):
    """上游 TestDistroRelease._test_outcome 等价构造（显式 release 文件）。"""
    from distro.distro import LinuxDistribution

    return LinuxDistribution(
        include_lsb=False,
        os_release_file="path-to-non-existing-file",
        distro_release_file=release_file,
    )


def test_os_release_arch():
    """上游 TestOSRelease.test_arch_os_release 等价断言。"""
    d = _make_os_release(os.path.join(RESOURCES, "distros", "arch"))
    assert d.id() == "arch", f"arch id: {d.id()!r}"
    assert d.name() == "Arch Linux", f"arch name: {d.name()!r}"
    assert d.name(pretty=True) == "Arch Linux", f"arch pretty: {d.name(pretty=True)!r}"
    print("PASS: os-release parsing (arch): id=arch name='Arch Linux'")


def test_os_release_ubuntu14():
    """上游 TestOSRelease.test_ubuntu14_os_release 等价断言。"""
    d = _make_os_release(os.path.join(RESOURCES, "distros", "ubuntu14"))
    assert d.id() == "ubuntu", f"ubuntu14 id: {d.id()!r}"
    assert d.name() == "Ubuntu", f"ubuntu14 name: {d.name()!r}"
    assert d.version() == "14.04", f"ubuntu14 version: {d.version()!r}"
    assert d.version(pretty=True) == "14.04 (Trusty Tahr)", (
        f"ubuntu14 pretty: {d.version(pretty=True)!r}"
    )
    assert d.version(best=True) == "14.04.3", f"ubuntu14 best: {d.version(best=True)!r}"
    assert d.like() == "debian", f"ubuntu14 like: {d.like()!r}"
    assert d.codename() == "Trusty Tahr", f"ubuntu14 codename: {d.codename()!r}"
    print("PASS: os-release parsing (ubuntu14): id=ubuntu version=14.04 best=14.04.3 like=debian codename='Trusty Tahr'")


def test_os_release_centos7():
    """上游 TestOSRelease.test_centos7_os_release 等价断言。"""
    d = _make_os_release(os.path.join(RESOURCES, "distros", "centos7"))
    assert d.id() == "centos", f"centos7 id: {d.id()!r}"
    assert d.name() == "CentOS Linux", f"centos7 name: {d.name()!r}"
    assert d.name(pretty=True) == "CentOS Linux 7 (Core)", (
        f"centos7 pretty: {d.name(pretty=True)!r}"
    )
    assert d.version() == "7", f"centos7 version: {d.version()!r}"
    assert d.version(pretty=True) == "7 (Core)", f"centos7 pretty_version: {d.version(pretty=True)!r}"
    assert d.version(best=True) == "7", f"centos7 best: {d.version(best=True)!r}"
    assert d.like() == "rhel fedora", f"centos7 like: {d.like()!r}"
    assert d.codename() == "Core", f"centos7 codename: {d.codename()!r}"
    print("PASS: os-release parsing (centos7): id=centos version=7 like='rhel fedora' codename=Core")


def test_distro_release_centos5():
    """上游 TestDistroRelease.test_centos5_release 等价断言。

    显式指定 distro_release_file=etc/centos-release（centos5 无 os-release），
    验证 *-release 文件解析路径 + 版本三元组拆分。
    """
    release_file = os.path.join(
        RESOURCES, "distros", "centos5", "etc", "centos-release"
    )
    d = _make_distro_release(release_file)
    assert d.id() == "centos", f"centos5 id: {d.id()!r}"
    assert d.name() == "CentOS", f"centos5 name: {d.name()!r}"
    assert d.name(pretty=True) == "CentOS 5.11 (Final)", (
        f"centos5 pretty_name: {d.name(pretty=True)!r}"
    )
    assert d.version() == "5.11", f"centos5 version: {d.version()!r}"
    assert d.version(pretty=True) == "5.11 (Final)", f"centos5 pretty_version: {d.version(pretty=True)!r}"
    assert d.version(best=True) == "5.11", f"centos5 best: {d.version(best=True)!r}"
    assert d.codename() == "Final", f"centos5 codename: {d.codename()!r}"
    assert d.major_version() == "5", f"centos5 major: {d.major_version()!r}"
    assert d.minor_version() == "11", f"centos5 minor: {d.minor_version()!r}"
    print("PASS: distro-release parsing (centos5): id=centos version=5.11 codename=Final major=5 minor=11 (via centos-release file)")


def test_distro_release_arch():
    """上游 TestDistroRelease.test_arch_dist_release 等价断言：空 release 文件。"""
    release_file = os.path.join(
        RESOURCES, "distros", "arch", "etc", "arch-release"
    )
    d = _make_distro_release(release_file)
    assert d.id() == "arch", f"arch dist-release id: {d.id()!r}"
    print("PASS: distro-release parsing (arch): empty arch-release file still yields id=arch (basename pattern)")


def test_unknown_distro_semantics():
    """上游 TestOSRelease.test_unknown_distro 等价断言：无任何 release 文件。"""
    with tempfile.TemporaryDirectory() as empty_root:
        d = _make_os_release(empty_root)
        assert d.id() == "", f"unknown id: {d.id()!r}"
        assert d.name() == "", f"unknown name: {d.name()!r}"
        assert d.version() == "", f"unknown version: {d.version()!r}"
        assert d.like() == "", f"unknown like: {d.like()!r}"
        assert d.codename() == "", f"unknown codename: {d.codename()!r}"
        info = d.info()
        assert info["id"] == "" and info["version"] == "", f"unknown info: {info}"
    print("PASS: unknown-distro semantics: empty id/name/version/like/codename (correct unknown branch)")


def test_repr():
    """上游 TestRepr 等价断言：repr(LinuxDistribution) 可读。"""
    d = _make_os_release(os.path.join(RESOURCES, "distros", "arch"))
    r = repr(d)
    assert "LinuxDistribution" in r, f"repr missing class name: {r!r}"
    print(f"PASS: repr(): {r[:90]}")


def test_linux_distribution_compat():
    """上游 linux_distribution() 兼容 API（含 DeprecationWarning）。"""
    import warnings

    import distro

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = distro.linux_distribution(full_distribution_name=True)
    assert isinstance(result, tuple) and len(result) == 3, (
        f"linux_distribution returned {result!r}"
    )
    print(f"PASS: linux_distribution() compat API returns 3-tuple: {result}")


def test_os_release_attr_and_info_keys():
    """上游 TestOSReleaseAttr / TestInfo 等价断言：info() 键完整性 + 属性查询。"""
    d = _make_os_release(os.path.join(RESOURCES, "distros", "ubuntu14"))
    info = d.info()
    expected_keys = {
        "id", "version", "version_parts", "like", "codename",
    }
    assert expected_keys.issubset(info.keys()), f"info keys: {sorted(info.keys())}"
    vp = info["version_parts"]
    assert vp == {"major": "14", "minor": "04", "build_number": ""}, f"version_parts: {vp}"
    assert d.os_release_attr("support_url") == "http://help.ubuntu.com/", (
        f"ubuntu14 support_url: {d.os_release_attr('support_url')!r}"
    )
    assert d.os_release_info().get("id") == "ubuntu", (
        f"os_release_info id: {d.os_release_info().get('id')!r}"
    )
    print("PASS: info() keys + version_parts + os_release_attr(support_url) + os_release_info()")


def test_ohos_host_behavior():
    """OHOS 本机行为断言：本机（root_dir=None）无 /etc/os-release 时返回空值。

    这是 distro 在 OHOS 上的实际平台行为（上游 IS_LINUX 门卫在
    sys.platform=='ohos' 上同样跳过 host 相关用例）——库本身工作正常，
    只是 OHOS 不提供 /etc/os-release 等标准发行版元数据文件，
    所有查询走 unknown 分支返回空值，符合预期语义，非适配缺陷。
    """
    import distro

    d = distro.LinuxDistribution(
        include_lsb=False,
        distro_release_file="path-to-non-existing-file",
    )
    # 无论本机是否有 os-release，调用均不应抛异常，返回 str
    for getter in (d.id, d.name, d.version, d.like, d.codename):
        val = getter()
        assert isinstance(val, str), f"{getter} returned non-str: {val!r}"
    has_os_release = os.path.isfile("/etc/os-release")
    if not has_os_release:
        # OHOS 无 /etc/os-release → unknown 分支返回空串
        assert d.id() == "", f"OHOS host id should be '' (no os-release): {d.id()!r}"
        print("PASS: OHOS host behavior: no /etc/os-release -> unknown branch (empty id/name), no exception")
    else:
        print(f"PASS: host has /etc/os-release, id={d.id()!r} (real host detection works)")


def test_cli_module():
    """CLI 入口：python -m distro 执行成功（上游 Makefile test_cli 同源）。"""
    result = subprocess.run(
        [sys.executable, "-m", "distro"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"python -m distro failed rc={result.returncode}: {result.stderr[:200]}"
    )
    assert "Name:" in result.stdout, f"CLI stdout missing 'Name:': {result.stdout[:100]}"
    print(f"PASS: CLI 'python -m distro' rc=0, stdout: {result.stdout.strip()[:60]!r}")


if __name__ == "__main__":
    tests = [
        test_import_and_version,
        test_os_release_arch,
        test_os_release_ubuntu14,
        test_os_release_centos7,
        test_distro_release_centos5,
        test_distro_release_arch,
        test_unknown_distro_semantics,
        test_repr,
        test_linux_distribution_compat,
        test_os_release_attr_and_info_keys,
        test_ohos_host_behavior,
        test_cli_module,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"FAIL: {fn.__name__}: {e}", file=sys.stderr)
            failed += 1
    if failed:
        print(f"\n{failed} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
    print(f"\nAll {len(tests)} python3-distro consumer tests passed.")
    sys.exit(0)
