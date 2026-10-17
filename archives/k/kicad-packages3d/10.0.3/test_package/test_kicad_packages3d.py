#!/usr/bin/env python3
"""kicad-packages3d 消费者测试（适配新增，OHOS 侧真实消费被测包）。

上游 kicad-packages3d 10.0.3 仓库**不含任何测试程序**（审计证据）：
  * 顶层 ``CMakeLists.txt`` 为 ``project(kicad-packages3d NONE)``，只有
    ``list_models``/``uninstall`` 自定义目标与 ``install(DIRECTORY *.3dshapes …)``，
    **没有 ``enable_testing`` / ``add_test`` / ``include(CTest)`` / ``BUILD_TESTING``**；
  * 仓库内 **0 个 C/C++ 源文件、0 个 Python/shell 脚本**（全部 7410 个条目中仅
    7238 个 ``*.step`` 模型 + 105 个 ``*.3dshapes`` 目录 + 文档/CMake 文件）；
  * 上游仓库没有 ``.gitlab-ci.yml`` 或任何 CI 测试配置（仅 ``.github/lockdown.yml``，
    是 GitHub issue 锁定机器人配置，非测试）。

因此上游测试注册总数为 **0**（``upstream_tests_exist: false``）。本测试以**自包含**
方式从消费者视角真实消费被测包：校验安装布局、模型覆盖度、STEP 文件有效性与若干
已知经典模型的存在性。仅依赖标准库，可直接在 OHOS CI worker 的 python3 上运行。

用法: test_kicad_packages3d.py <package_folder>
"""
import glob
import json
import os
import sys

MODELS_SUBDIR = os.path.join("share", "kicad", "3dmodels")

# 已知经典模型：(3dshapes 目录, 期望至少包含的 STEP 文件数, 抽样文件名)
# 目录名、期望下限与抽样文件名为 tag 10.0.3 的确定实测值（源码 sha256 固定）。
#   各目录 STEP 文件数实测：Resistor_SMD 40、Package_DIP 204、Package_TO_SOT_THT 93、
#   Capacitor_SMD 91、Diode_SMD 38。
KNOWN_MODELS = [
    ("Resistor_SMD", 40, "R_01005_0402Metric.step"),
    ("Package_DIP", 200, "DIP-10_W7.62mm.step"),
    ("Package_TO_SOT_THT", 90, "Analog_TO-46-4_ThermalShield.step"),
    ("Capacitor_SMD", 90, "CP_Elec_10x10.step"),
    ("Diode_SMD", 35, "D_0603_1608Metric.step"),
]


class Checker:
    """极简断言收集器：逐条记录 PASS/FAIL，最后统一给退出码。"""

    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0

    def check(self, ok, label, detail=""):
        if ok:
            self.passed += 1
            print("  [OK]   %s%s" % (label, (" — " + detail) if detail else ""))
        else:
            self.failed += 1
            print("  [FAIL] %s%s" % (label, (" — " + detail) if detail else ""))
        return ok

    def report(self):
        total = self.passed + self.failed
        print("\n%s: %d/%d assertions passed" % (self.name, self.passed, total))
        return self.failed == 0


def step_file_ok(path):
    """STEP (ISO-10303-21) 文件有效性：非空、以头尾标记闭合、可读文本。"""
    try:
        with open(path, "rb") as fh:
            head = fh.read(128)
            fh.seek(-128, os.SEEK_END)
            tail = fh.read(128)
    except OSError:
        return False
    if not head or not tail.strip():
        return False
    # 头尾用字节前缀/后缀判断，容忍文件可能以 CRLF 或空白结尾
    if not head.lstrip().startswith(b"ISO-10303-21;"):
        return False
    if b"END-ISO-10303-21;" not in tail:
        return False
    return True


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_ROOT", "")
    if not pkg_root or not os.path.isdir(pkg_root):
        print("ERROR: package folder not given or not a directory: %r" % pkg_root,
              file=sys.stderr)
        return 2

    # 只读包目录（Conan 缓存/HMDFS 上可能不可写），全程只读不写
    models_dir = os.path.join(pkg_root, MODELS_SUBDIR)

    ck = Checker("kicad-packages3d consumer test")

    # ── 1. 安装布局（与上游 CMake install 及 Debian 官方包同构） ─────────────
    print("[1] installed layout")
    ck.check(os.path.isdir(models_dir), "share/kicad/3dmodels exists", models_dir)
    ck.check(os.path.isfile(os.path.join(pkg_root, "licenses", "LICENSE.md")),
             "licenses/LICENSE.md shipped")
    if not os.path.isdir(models_dir):
        print("\nRESULT: FAILED (package layout incomplete)")
        return 1

    # 收集所有 .3dshapes 目录与 .step 文件
    shape_dirs = sorted(
        d for d in os.listdir(models_dir)
        if os.path.isdir(os.path.join(models_dir, d)) and d.endswith(".3dshapes")
    )
    step_files = sorted(glob.glob(os.path.join(models_dir, "*", "*.step")))
    resolved_steps = [os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p)
                      for p in step_files]

    ck.check(len(shape_dirs) == 105, "3dshapes categories present",
             "%d dirs (upstream tag 10.0.3 has 105)" % len(shape_dirs))
    ck.check(len(step_files) == 7238, "installed STEP model count",
             "%d models (upstream tag 10.0.3 has 7238)" % len(step_files))

    # ── 2. 每个 3dshapes 目录都必须非空（无空模型库） ────────────────────────
    print("[2] model coverage")
    empty_dirs = [d for d in shape_dirs
                  if not glob.glob(os.path.join(models_dir, d, "*.step"))]
    ck.check(not empty_dirs, "no empty 3dshapes library",
             ", ".join(empty_dirs[:5]) if empty_dirs else "")

    # ── 3. STEP 文件有效性（ISO-10303-21 头/尾闭合、非空） ──────────────────
    print("[3] STEP file validity")
    bad_steps = [os.path.relpath(p, models_dir) for p in step_files
                 if not step_file_ok(p)]
    ck.check(not bad_steps, "every .step is a well-formed ISO-10303-21 file",
             ", ".join(bad_steps[:5]) if bad_steps else "%d files checked" % len(step_files))

    # ── 4. 已知经典模型存在性 ──────────────────────────────────────────────
    print("[4] known model presence")
    installed = set(resolved_steps)
    for shp, min_count, sample in KNOWN_MODELS:
        names = {os.path.relpath(p, models_dir) for p in step_files
                 if os.path.dirname(os.path.relpath(p, models_dir)) == shp + ".3dshapes"}
        ck.check(len(names) > 0, "%s.3dshapes non-empty" % shp,
                 "%d models" % len(names))
        if min_count is not None:
            ck.check(len(names) >= min_count,
                     "%s.3dshapes model count" % shp,
                     "expected >= %d, found %d" % (min_count, len(names)))
        if sample:
            sample_id = "%s.3dshapes/%s" % (shp, sample)
            ck.check(sample_id in installed, "known model %s" % sample_id)

    ok = ck.report()
    print("\nRESULT: %s" % ("PASSED" if ok else "FAILED"))

    # HMBS 机器证据标记：单行、独立 JSON 对象，值只含标记自身的五个字段。
    # 不得再包一层 {"HMBS_TEST_PACKAGE_RESULT": ..., "checks": ...}——那会使
    # 整行不再是合法独立 JSON，门禁按 `HMBS_TEST_PACKAGE_RESULT={...}` 解析时
    # 会因行尾多余的 ", "checks": ...}" 解析失败，判为"缺少真实用例计数/证据"。
    marker = {
        "executed": True,
        "passed": ok,
        "command": "python3 -B test_kicad_packages3d.py <package_folder>",
        "discovered": ck.passed + ck.failed,
        "passedCount": ck.passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
