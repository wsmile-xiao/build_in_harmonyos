#!/usr/bin/env python3
"""lomiri-schemas 安装产物功能断言（鸿蒙特有，OHOS 目标实跑）。

用法: python3 test_lomiri_schemas.py <lomiri-schemas-pkg> <glib-pkg>

覆盖：
  A. GSettings schema：6 个文件齐全、良构 XML、15 个 <schema id> 全部就位
  B. glib-compile-schemas --strict --dry-run 对 schema 目录做真实编译校验
     （GSettings 运行期接受的模式合法性，与上游 add_schema 的 validate-*
     同源；后端用 glib 包自带的 glib-compile-schemas）
  C. lomiri-schemas.pc：存在、Version 0.1.11、Requires glib-2.0、prefix 已重定位
  D. AccountsService：6 个 D-Bus 接口 XML + accountsservice/interfaces 入口
  E. polkit policy 与 rules
"""
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

SCHEMAS = [
    "com.lomiri.notifications.settings.gschema.xml",
    "com.lomiri.phone.gschema.xml",
    "com.lomiri.Shell.gschema.xml",
    "com.lomiri.sound.gschema.xml",
    "com.lomiri.touch.sound.gschema.xml",
    "com.lomiri.touch.system.gschema.xml",
]

SCHEMA_IDS = [
    "com.lomiri.notifications.settings",
    "com.lomiri.notifications.settings.applications",
    "com.lomiri.phone",
    "com.lomiri.Shell",
    "com.lomiri.Shell.Greeter",
    "com.lomiri.Shell.Interface",
    "com.lomiri.Shell.Launcher",
    "com.lomiri.Shell.Devices",
    "com.lomiri.Shell.Decorations",
    "com.lomiri.Shell.IntegratedMenus",
    "com.lomiri.Shell.Gestures",
    "com.lomiri.Shell.Shortcuts",
    "com.lomiri.sound",
    "com.lomiri.touch.sound",
    "com.lomiri.touch.system",
]

ACCOUNTS_XML = [
    "com.lomiri.AccountsService.Input.xml",
    "com.lomiri.AccountsService.SecurityPrivacy.xml",
    "com.lomiri.AccountsService.Sound.xml",
    "com.lomiri.touch.AccountsService.Phone.xml",
    "com.lomiri.touch.AccountsService.SecurityPrivacy.xml",
    "com.lomiri.touch.AccountsService.Sound.xml",
]

POLICY = "com.lomiri.AccountsService.policy"
RULES = "50-com.lomiri.AccountsService.rules"

TOTAL = 0
FAILED = []


def check(condition, message):
    global TOTAL
    TOTAL += 1
    if not condition:
        FAILED.append(message)
        print(f"FAIL: {message}", file=sys.stderr)
    return bool(condition)


def main():
    pkg, glib = sys.argv[1], sys.argv[2]
    schemadir = os.path.join(pkg, "share", "glib-2.0", "schemas")

    # ── A. schema 文件 ────────────────────────────────────────────
    check(os.path.isdir(schemadir), f"schema dir missing: {schemadir}")

    found_ids = set()
    for name in SCHEMAS:
        path = os.path.join(schemadir, name)
        if not check(os.path.isfile(path), f"schema file missing: {path}"):
            continue
        try:
            root = ET.parse(path).getroot()
            parsed = True
        except ET.ParseError as exc:
            parsed = False
            print(f"      {exc}", file=sys.stderr)
        check(parsed, f"schema not well-formed XML: {name}")
        if parsed:
            for node in root.iter("schema"):
                found_ids.add(node.get("id"))

    for schema_id in SCHEMA_IDS:
        check(schema_id in found_ids, f"schema id missing: {schema_id}")

    # ── B. glib-compile-schemas 真实编译校验 ─────────────────────
    compiler = os.path.join(glib, "bin", "glib-compile-schemas")
    if not check(os.path.isfile(compiler), f"glib-compile-schemas missing: {compiler}"):
        pass
    else:
        proc = subprocess.run(
            [compiler, "--strict", "--dry-run", schemadir],
            capture_output=True, text=True,
        )
        check(
            proc.returncode == 0,
            "glib-compile-schemas --strict --dry-run failed: "
            f"rc={proc.returncode} {proc.stdout.strip()} {proc.stderr.strip()}",
        )

    # ── C. pkg-config 元数据 ─────────────────────────────────────
    pc = os.path.join(pkg, "share", "pkgconfig", "lomiri-schemas.pc")
    if check(os.path.isfile(pc), f"pc file missing: {pc}"):
        body = open(pc, encoding="utf-8").read()
        check("Version: 0.1.11" in body, "pc Version is not 0.1.11")
        check("Requires: glib-2.0" in body, "pc does not require glib-2.0")
        check("${pcfiledir}" in body, "pc prefix was not relocated")

    # ── D. AccountsService D-Bus 接口 ────────────────────────────
    dbus_dir = os.path.join(pkg, "share", "dbus-1", "interfaces")
    svc_dir = os.path.join(pkg, "share", "accountsservice", "interfaces")
    for name in ACCOUNTS_XML:
        check(os.path.isfile(os.path.join(dbus_dir, name)),
              f"dbus interface missing: {name}")
        check(os.path.exists(os.path.join(svc_dir, name)),
              f"accountsservice interface entry missing: {name}")

    # ── E. polkit ────────────────────────────────────────────────
    check(os.path.isfile(os.path.join(pkg, "share", "polkit-1", "actions", POLICY)),
          f"polkit action missing: {POLICY}")
    check(os.path.isfile(os.path.join(pkg, "share", "polkit-1", "rules.d", RULES)),
          f"polkit rule missing: {RULES}")

    if FAILED:
        print(f"\nFAILED: {len(FAILED)}/{TOTAL}", file=sys.stderr)
        return 1
    print(f"OK: {TOTAL}/{TOTAL} lomiri-schemas assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
