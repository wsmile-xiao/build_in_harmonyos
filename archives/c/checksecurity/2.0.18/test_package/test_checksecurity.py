#!/usr/bin/env python3
"""checksecurity consumer test (L0c: standalone test source executed via
self.run from conanfile.py test()).

checksecurity 是 Debian 系统安全检查脚本集：主脚本 bin/checksecurity
（perl）驱动 share/checksecurity/check-* 插件。主脚本运行需 root 权限
（非 root 输出 "Sorry, only root can run checksecurity" 后退出 1），
故本测试对 Perl 组件做真实语法校验（perl -c，验证 OHOS perl 与补丁后的
shebang 兼容），并逐项核对 5 个插件 + 配置文件的打包完整性。

Usage: test_checksecurity.py <package-folder>
"""
import os
import subprocess
import sys

MAIN_SCRIPT = "bin/checksecurity"
PLUGIN_DIR = os.path.join("share", "checksecurity")
# perl 绝对路径（conanrun PATH 不含相对名 perl——本包无 requires perl，
# backup2l 先例同款教训：subprocess 相对名命令在 conanrun 环境抛
# FileNotFoundError；backup2l 用 /data/service/hnp/bin/bash 解决）
PERL_BIN = os.environ.get("PERL", "/data/service/hnp/bin/perl")
PLUGINS = [
    "check-diskfree",      # sh
    "check-iptables-logs",  # perl
    "check-passwd",        # sh
    "check-setuid",        # sh
    "check-sockets",       # sh
]
CONF_FILES = [
    "check-diskfree.conf",
    "check-passwd.conf",
    "check-setuid.conf",
    "check-socket.conf",
    "global-checksecurity.conf",
]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]

    # 1. 主脚本存在
    main_path = os.path.join(pkg, *MAIN_SCRIPT.split("/"))
    if not os.path.isfile(main_path):
        raise AssertionError(f"checksecurity main script missing: {main_path}")
    print(f"OK: main script present ({main_path})")

    # 2. 主脚本 perl 语法校验（验证补丁后 shebang + OHOS perl 可解析）
    r = subprocess.run([PERL_BIN, "-c", main_path], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"checksecurity perl syntax invalid: {r.stderr}")
    print(f"OK: main script perl syntax valid")

    # 3. 5 个插件齐全 + perl 插件语法校验
    for pl in PLUGINS:
        p = os.path.join(pkg, PLUGIN_DIR, pl)
        if not os.path.isfile(p):
            raise AssertionError(f"plugin missing: {p}")
        print(f"OK: plugin present ({pl})")
        if pl == "check-iptables-logs":
            r = subprocess.run([PERL_BIN, "-c", p], capture_output=True, text=True)
            if r.returncode != 0:
                raise AssertionError(f"{pl} perl syntax invalid: {r.stderr}")
            print(f"OK: plugin perl syntax valid ({pl})")

    # 4. 配置文件齐全
    conf_dir = os.path.join(pkg, "etc", "checksecurity")
    for cf in CONF_FILES:
        c = os.path.join(conf_dir, cf)
        if not os.path.isfile(c):
            raise AssertionError(f"config missing: {c}")
    print(f"OK: {len(CONF_FILES)} config files present")

    print("OK: checksecurity package consumable")
    return 0


if __name__ == "__main__":
    sys.exit(main())