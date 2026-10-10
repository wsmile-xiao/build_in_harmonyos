#!/usr/bin/env python3
"""test_ohos — playerctl 2.4.1 HarmonyOS PC 消费者专项用例（适配方新增）

上游 playerctl 自带的自动化测试是 test/ 下的 pytest 套件（18 用例），运行前提是
一个真实可用的 D-Bus session bus（test/conftest.py 用 `dbus-launch` 拉起，再向该
bus export org.mpris.MediaPlayer2.<name> 服务）。OHOS 构建/CI 沙箱无 machine-id、
/etc 与 /var 只读、无 dbus-daemon 服务目录，pytest 套件无法在其中执行。

因此本文件按 R51「适配后新增至少一个鸿蒙消费者用例」的要求，提供一组**自包含、
不依赖 session bus / pytest / 网络**的鸿蒙消费者用例：直接消费最终 Conan 包
（读公共头 + 链接 libplayerctl.so + 执行安装后的 CLI），验证产物在 OHOS 上真实可用。

本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）。

用法:
    python3 run_ohos_test.py <conan_package_folder> [glib_package_folder]

    glib_package_folder 省略时自动在 conan 缓存中探测（$CONAN_HOME 或 ~/.conan2
    下 p/glib*/p，需含 lib/libgobject-2.0.so.0）。可用环境变量
    PLAYERCTL_GLIB_FOLDER 显式指定。

退出码: 0=全部通过；1=有失败（打印首个失败详情）；2=用法错误。

用例清单（详见 MANIFEST.yml）:
  T1 aarch64_elf           三个 ELF 均为 ELF64 AArch64
  T2 musl_no_glibc         musl libc，无 GLIBC 符号版本、无 ld-linux
  T3 codesign              .codesign 段存在（OHOS 签名管线产出）
  T4 no_host_paths         无 RPATH/RUNPATH，无宿主绝对路径泄漏
  T5 so_alias_materialized libplayerctl.so/.so.2 已物化为同尺寸常规文件
  T6 pkgconfig_metadata    playerctl.pc 的 Name/Version/Libs 正确
  T7 cli_real_execution    真实执行 bin/playerctl（--version/--help）与 bin/playerctld
  T8 linked_consumer       真实编译+链接+运行 C 消费者，调用公共 API（深拷贝语义）
"""

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF") or shutil.which("llvm-readelf") \
    or shutil.which("readelf") or "readelf"
STRINGS = os.environ.get("STRINGS") or shutil.which("llvm-strings") \
    or shutil.which("strings") or "strings"
CC = os.environ.get("CC") or shutil.which("clang") or shutil.which("cc") or "clang"

HOST_PATH_PATTERNS = (b"/storage/", b"/Users/", b"/data/storage/", b"/home/",
                      b"playerctl-2.4.1")

ELF_TARGETS = ("bin/playerctl", "bin/playerctld", "lib/libplayerctl.so.2.4.1")

# T8 内联 C 消费者：只经公开头 <playerctl/playerctl.h> 与 -lplayerctl 链接，
# 调用公共 API 验证 boxed 类型注册与深拷贝语义（无 session bus、无临时文件）。
CONSUMER_C = r"""
#include <stdio.h>
#include <string.h>
#include <glib.h>
#include <playerctl/playerctl.h>

int main(void)
{
    const char *original = "org.mpris.MediaPlayer2.playerctl-ohos";
    PlayerctlPlayerName source;
    PlayerctlPlayerName *copy;
    gchar *name_buf;
    GType type;

    if (strcmp(PLAYERCTL_VERSION_S, "2.4.1") != 0) {
        printf("FAIL: PLAYERCTL_VERSION_S=%s\n", PLAYERCTL_VERSION_S);
        return 1;
    }

    type = playerctl_player_name_get_type();
    if (type == 0 || g_type_name(type) == NULL
            || strcmp(g_type_name(type), "PlayerctlPlayerName") != 0) {
        printf("FAIL: PlayerctlPlayerName boxed type not registered\n");
        return 2;
    }
    if (!G_TYPE_IS_ENUM(playerctl_source_get_type())) {
        printf("FAIL: PlayerctlSource is not a registered GEnum\n");
        return 3;
    }

    name_buf = g_strdup(original);
    source.name = name_buf;
    source.instance = g_strdup("org.mpris.MediaPlayer2.playerctl-ohos.instance");
    source.source = PLAYERCTL_SOURCE_DBUS_SESSION;

    copy = playerctl_player_name_copy(&source);
    if (copy == NULL || copy == &source) {
        printf("FAIL: playerctl_player_name_copy() did not allocate\n");
        return 4;
    }
    if (copy->name == name_buf || copy->name == NULL
            || strcmp(copy->name, original) != 0) {
        printf("FAIL: copy->name is not a deep copy\n");
        return 5;
    }
    if (strcmp(copy->instance, source.instance) != 0
            || copy->source != PLAYERCTL_SOURCE_DBUS_SESSION) {
        printf("FAIL: copy->instance/source not preserved\n");
        return 6;
    }
    name_buf[0] = 'X';
    if (strcmp(copy->name, original) != 0) {
        printf("FAIL: copy aliases the source string\n");
        return 7;
    }

    playerctl_player_name_free(copy);
    g_free(name_buf);
    g_free(source.instance);

    printf("OHOS_PLAYERCTL_CONSUMER_PASS version=%s type=%s\n",
           PLAYERCTL_VERSION_S, g_type_name(type));
    return 0;
}
"""


class Failure(Exception):
    pass


def run(argv, **kwargs):
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    return subprocess.run(argv, **kwargs)


def find_glib_folder(pkg_folder):
    """探测 glib 包目录：env 优先，其次扫描 conan 缓存。"""
    explicit = os.environ.get("PLAYERCTL_GLIB_FOLDER")
    candidates = []
    if explicit:
        candidates.append(explicit)
    for home in (os.environ.get("CONAN_HOME"),
                 os.path.expanduser("~/.conan2"),
                 os.path.expanduser("~/.cache/conan2")):
        if home:
            candidates.extend(sorted(glob.glob(os.path.join(home, "p", "glib*", "p"))))
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "lib", "libgobject-2.0.so.0")):
            return candidate
    return None


def elf_targets(pkg):
    return [os.path.join(pkg, relative) for relative in ELF_TARGETS]


def check_prerequisites(pkg):
    missing = [p for p in elf_targets(pkg) if not os.path.isfile(p)]
    if missing:
        raise Failure("missing package artifacts: %s" % ", ".join(missing))


def t1_aarch64_elf(pkg):
    for target in elf_targets(pkg):
        result = run([READELF, "-h", target])
        header = (result.stdout or "") + (result.stderr or "")
        if "ELF64" not in header or "AArch64" not in header:
            raise Failure("T1 %s: not ELF64 AArch64" % os.path.relpath(target, pkg))
    return "3 ELF are ELF64 AArch64 (bin/playerctl, bin/playerctld, lib/libplayerctl.so.2.4.1)"


def t2_musl_no_glibc(pkg):
    for target in elf_targets(pkg):
        dyn = run([READELF, "-d", target]).stdout or ""
        if "GLIBC" in dyn or "ld-linux" in dyn:
            raise Failure("T2 %s: glibc/ld-linux dependency detected"
                          % os.path.relpath(target, pkg))
        if "libc.so" not in dyn:
            raise Failure("T2 %s: no musl libc.so in NEEDED"
                          % os.path.relpath(target, pkg))
    return "musl libc only: no GLIBC symbol versions, no ld-linux; libc.so present"


def t3_codesign(pkg):
    for target in elf_targets(pkg):
        sections = run([READELF, "-S", target]).stdout or ""
        if ".codesign" not in sections:
            raise Failure("T3 %s: .codesign section missing"
                          % os.path.relpath(target, pkg))
    return ".codesign present in all 3 ELF (OHOS signing pipeline output)"


def t4_no_host_paths(pkg):
    for target in elf_targets(pkg):
        dyn = run([READELF, "-d", target]).stdout or ""
        for keyword in ("RPATH", "RUNPATH"):
            if keyword in dyn:
                raise Failure("T4 %s: %s present in dynamic section"
                              % (os.path.relpath(target, pkg), keyword))
        blob = run([STRINGS, target]).stdout or ""
        encoded = blob.encode("utf-8", "replace")
        for pattern in HOST_PATH_PATTERNS:
            if pattern in encoded:
                raise Failure("T4 %s: host path leak %s"
                              % (os.path.relpath(target, pkg), pattern.decode()))
    return "no RPATH/RUNPATH, no absolute host path leak in 3 ELF"


def t5_so_alias_materialized(pkg):
    libdir = os.path.join(pkg, "lib")
    names = ("libplayerctl.so.2.4.1", "libplayerctl.so.2", "libplayerctl.so")
    sizes = {}
    for name in names:
        path = os.path.join(libdir, name)
        if not os.path.isfile(path) or os.path.islink(path):
            raise Failure("T5 %s: missing or not a regular file" % name)
        sizes[name] = os.path.getsize(path)
    if len(set(sizes.values())) != 1:
        raise Failure("T5 .so alias sizes differ: %s" % sizes)
    return ("libplayerctl.so / .so.2 materialized as regular files, "
            "%d bytes each (symlinkat unsupported on HMDFS)" % sizes[names[0]])


def t6_pkgconfig_metadata(pkg):
    pc_file = os.path.join(pkg, "lib", "pkgconfig", "playerctl.pc")
    if not os.path.isfile(pc_file):
        raise Failure("T6 playerctl.pc missing")
    with open(pc_file, encoding="utf-8") as handle:
        content = handle.read()
    fields = {}
    for line in content.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()
    expected = {"name": "Playerctl", "version": "2.4.1"}
    for key, want in expected.items():
        if fields.get(key) != want:
            raise Failure("T6 playerctl.pc %s = %r (want %r)"
                          % (key, fields.get(key), want))
    if "-lplayerctl" not in fields.get("libs", ""):
        raise Failure("T6 playerctl.pc Libs lacks -lplayerctl: %r"
                      % fields.get("libs"))
    return "playerctl.pc Name=Playerctl Version=2.4.1 Libs=-L${libdir} -lplayerctl"


def cli_env(pkg, glib_folder):
    libdirs = [os.path.join(pkg, "lib")]
    if glib_folder:
        libdirs.append(os.path.join(glib_folder, "lib"))
    # glib 的传递依赖（libffi/pcre2/zlib 等）若为共享构建，同样需要可见
    for extra in sorted(glob.glob(os.path.join(
            os.path.expanduser("~/.conan2"), "p", "*", "p", "lib"))):
        if os.path.isdir(extra):
            libdirs.append(extra)
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs)
    env.setdefault("TMPDIR", os.path.expanduser("~/.cache"))
    return env


def t7_cli_real_execution(pkg, env):
    cases = (
        ("bin/playerctl", ["--version"], "v2.4.1"),
        ("bin/playerctl", ["--help"], "Controller for media players"),
        ("bin/playerctld", ["--help"], "Playerctl Daemon"),
    )
    details = []
    for relative, args, needle in cases:
        binary = os.path.join(pkg, relative)
        result = run([binary] + args, env=env)
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            raise Failure("T7 %s %s: exit %d (%s)"
                          % (relative, " ".join(args), result.returncode,
                             output.strip()[:200]))
        if needle not in output:
            raise Failure("T7 %s %s: output lacks %r (%s)"
                          % (relative, " ".join(args), needle, output.strip()[:200]))
        details.append("%s %s -> exit 0" % (relative, " ".join(args)))
    return "; ".join(details)


def t8_linked_consumer(pkg, glib_folder, env):
    work = tempfile.mkdtemp(prefix="playerctl-ohos-")
    if glib_folder is None:
        raise Failure("T8 glib package folder not found; set PLAYERCTL_GLIB_FOLDER")
    src = os.path.join(work, "ohos_consumer.c")
    with open(src, "w", encoding="utf-8") as handle:
        handle.write(CONSUMER_C)
    exe = os.path.join(work, "ohos_consumer")

    cmd = [CC, "-O2", "-Wall",
           "-I" + os.path.join(pkg, "include"),
           "-I" + os.path.join(glib_folder, "include"),
           "-I" + os.path.join(glib_folder, "include", "glib-2.0"),
           "-I" + os.path.join(glib_folder, "lib", "glib-2.0", "include"),
           src,
           "-L" + os.path.join(pkg, "lib"),
           "-L" + os.path.join(glib_folder, "lib"),
           "-lplayerctl", "-lgobject-2.0", "-lglib-2.0", "-lm",
           "-o", exe]
    compiled = run(cmd)
    if compiled.returncode != 0:
        raise Failure("T8 compile/link failed:\n%s" % (compiled.stderr or "")[:1500])

    executed = run([exe], env=env)
    output = (executed.stdout or "") + (executed.stderr or "")
    if executed.returncode != 0 or "OHOS_PLAYERCTL_CONSUMER_PASS" not in output:
        raise Failure("T8 consumer run failed rc=%d: %s"
                      % (executed.returncode, output.strip()[:1500]))
    return output.strip()


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: run_ohos_test.py <conan_package_folder> [glib_package_folder]",
              file=sys.stderr)
        return 2
    pkg = os.path.abspath(sys.argv[1])
    glib_folder = os.path.abspath(sys.argv[2]) if len(sys.argv) == 3 else None
    if glib_folder is None:
        glib_folder = find_glib_folder(pkg)

    print("test_ohos — playerctl 2.4.1 HarmonyOS PC consumer checks")
    print("package: %s" % pkg)
    print("glib   : %s" % (glib_folder or "<not found>"))
    print("tools  : readelf=%s strings=%s cc=%s" % (READELF, STRINGS, CC))
    print("")

    try:
        check_prerequisites(pkg)
        env = cli_env(pkg, glib_folder)
        results = [
            ("T1_aarch64_elf", t1_aarch64_elf(pkg)),
            ("T2_musl_no_glibc", t2_musl_no_glibc(pkg)),
            ("T3_codesign", t3_codesign(pkg)),
            ("T4_no_host_paths", t4_no_host_paths(pkg)),
            ("T5_so_alias_materialized", t5_so_alias_materialized(pkg)),
            ("T6_pkgconfig_metadata", t6_pkgconfig_metadata(pkg)),
            ("T7_cli_real_execution", t7_cli_real_execution(pkg, env)),
            ("T8_linked_consumer", t8_linked_consumer(pkg, glib_folder, env)),
        ]
    except Failure as failure:
        print("FIRST FAILURE: %s" % failure, file=sys.stderr)
        return 1

    for name, detail in results:
        print("PASS %s: %s" % (name, detail))
    print("")
    print("TEST_OHOS_ALL_PASS (%d/%d)" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
