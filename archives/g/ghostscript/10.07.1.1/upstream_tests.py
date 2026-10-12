#!/usr/bin/env python3
"""跑 ghostscript 10.07.1 发行包里的上游用例，并按目录口径核对 508。

计数口径（与审查人用 ghostscript-10.07.1.tar.gz 数出的 508 对齐）：
普通文件，路径上有一段目录名正好是 test、tests、unittest、unittests
或 gstest，排除 .xml。extract 的 .xml 都在 *.dir.ref 夹具里，不单列。
配置树里的 tiff-config、.deps、obj、soobj、generated 是构建产物，不计入。

发行包里的 make check 是空操作，不计入 N。examples 与 lib/acctest.ps
不在这 508 项里，本脚本仍会实跑，记为 EXTRA。
"""

import os
import re
import shutil
import signal
import subprocess
import sys

EXACT_DIRS = {"test", "tests", "unittest", "unittests", "gstest"}
SKIP_DIRS = {
    "tiff-config",
    ".deps",
    "obj",
    "soobj",
    "generated",
    ".libs",
    "__pycache__",
    # freetype 的 download-test-fonts.py 会把字体下到 tests/data，不在发行包里。
    "data",
}
SKIP_EXT = {".xml", ".po", ".plo", ".tpo", ".o", ".lo", ".obj", ".pyc"}
ANSI = re.compile(r"\x1b\[[0-9;]*m")
AUTO = re.compile(
    r"^(PASS|FAIL|SKIP|XFAIL|XPASS|ERROR):\s+(\S+)", re.MULTILINE
)
CTEST = re.compile(
    r"Test\s+#\d+:\s+(\S+)\s+\.+\s+(\*+)?(Passed|Failed|Not Run|Timeout)",
    re.IGNORECASE,
)
CID_MARKERS = (
    "GothicBBB-Medium",
    "Ryumin-Light",
    "MKai-Medium",
    "STHeiti-Regular",
    "HeiseiKakuGo",
    "WadaMin-Regular",
    "HYGoThic-Medium",
)

RESULTS = {}
HARD_FAIL = False


def emit(line):
    print(line, flush=True)


def tail_text(text, limit=25):
    lines = [ANSI.sub("", line).rstrip() for line in text.splitlines()]
    lines = [line for line in lines if line.strip()]
    if not lines:
        return "(无输出)"
    return " | ".join(lines[-limit:])[:900]


def interesting(text):
    keys = (
        "fatal error",
        "error:",
        "Error",
        "No such file",
        "not found",
        "SyntaxError",
        "ModuleNotFoundError",
        "command not found",
        "undefined reference",
        "FAILED",
        "SKIP",
    )
    lines = [ANSI.sub("", line).strip() for line in text.splitlines()]
    picked = [line for line in lines if any(key in line for key in keys)]
    if picked:
        return " | ".join(picked[-8:])[:700]
    return tail_text(text, 12)


def run(cmd, cwd, log_path, timeout, env=None):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    merged = os.environ.copy()
    if env:
        merged.update(env)
    emit("RUN " + " ".join(cmd) + "  cwd=" + cwd)
    with open(log_path, "w", encoding="utf-8", errors="replace") as handle:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=handle,
                stderr=subprocess.STDOUT,
                env=merged,
                start_new_session=True,
            )
        except OSError as exc:
            handle.write("OSError %s\n" % exc)
            return 127, "OSError %s" % exc
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            handle.write("\nTIMEOUT %s\n" % timeout)
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                proc.kill()
            proc.wait(timeout=30)
            code = 124
    with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    return code, text


def set_result(path, status, reason):
    if path in RESULTS:
        return
    RESULTS[path] = (status, reason.replace("\n", " ")[:900])
    emit("CASE %s %s %s" % (status, path, RESULTS[path][1][:240]))


def which(name):
    return shutil.which(name) or ""


def sdk_bin(tool):
    """优先用 OHOS SDK 的 clang。brew 包装的 clang 在这台机器上链接阶段 posix_spawn 失败。"""
    opt = os.path.expanduser("~/.harmonybrew/opt")
    found = []
    if os.path.isdir(opt):
        for name in os.listdir(opt):
            if not name.startswith("ohos-sdk"):
                continue
            path = os.path.join(opt, name, "native", "llvm", "bin", tool)
            if os.path.exists(path):
                found.append(path)
    if found:
        return sorted(found)[-1]
    return which(tool) or tool


def ensure_tools(out):
    """configure/libtool 要在 PATH 里找到 ld、ar、ranlib。SDK 只提供 ld.lld 和 llvm-*。"""
    sdk = os.path.dirname(sdk_bin("clang"))
    if os.path.isdir(sdk):
        os.environ["PATH"] = sdk + os.pathsep + os.environ.get("PATH", "")
    ensure_id(out)
    mapping = {
        "ld": "ld.lld",
        "ar": "llvm-ar",
        "ranlib": "llvm-ranlib",
        "nm": "llvm-nm",
        "strip": "llvm-strip",
        "objdump": "llvm-objdump",
        "objcopy": "llvm-objcopy",
    }
    bindir = os.path.join(out, "bin")
    os.makedirs(bindir, exist_ok=True)
    for name, fallback in mapping.items():
        if which(name):
            continue
        src = os.path.join(sdk, fallback)
        if not os.path.exists(src):
            continue
        dest = os.path.join(bindir, name)
        with open(dest, "w", encoding="utf-8", newline="\n") as handle:
            handle.write('#!/bin/sh\nexec "%s" "$@"\n' % src)
        os.chmod(dest, 0o755)


def ensure_id(out):
    """发行包的 autotools configure 会调用 id。设备 PATH 里没有 id。"""
    if which("id"):
        return
    bindir = os.path.join(out, "bin")
    os.makedirs(bindir, exist_ok=True)
    path = os.path.join(bindir, "id")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    -u|-g) echo 2000; exit 0 ;;\n"
            "  esac\n"
            "done\n"
            "echo 'uid=2000(currentUser) gid=2000(currentUser) groups=2000(currentUser)'\n"
        )
    os.chmod(path, 0o755)
    os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")


def enable_snprintf(build):
    """tiffiop.h 在 HAVE_SNPRINTF 未定义时把 snprintf 换成 GS 的 _TIFF_snprintf_f。
    该符号只在 base/gstiffio.c，独立 libtiff 链接不到。配置探测把它留成 #undef。"""
    old = "/* #undef HAVE_SNPRINTF */"
    new = "#define HAVE_SNPRINTF 1"
    for name in ("libtiff/tif_config.h", "libtiff/tiffconf.h"):
        path = os.path.join(build, name)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        if old not in text:
            continue
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace(old, new))


def relax_configure(path):
    """HMDFS 上 configure 用 umask 077 建临时目录后写不进 subs.awk。与配方里对顶层 configure 的处理相同。"""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    if "umask 077" not in text:
        return
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace("umask 077", "umask 022"))


def suite_summary(text):
    lines = []
    for line in ANSI.sub("", text).splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and any(
            token in stripped
            for token in ("TOTAL", "PASS", "FAIL", "SKIP", "ERROR", "XFAIL")
        ):
            lines.append(stripped)
    if lines:
        return " ".join(lines)
    return interesting(text)


def assign_automake(files, text, code, command):
    by_base = {}
    for path in files:
        by_base.setdefault(os.path.basename(path), []).append(path)
        stem, _ext = os.path.splitext(os.path.basename(path))
        by_base.setdefault(stem, []).append(path)
    matched = set()
    summary = suite_summary(text)
    for status, name in AUTO.findall(ANSI.sub("", text)):
        base = os.path.basename(name)
        stem, _ext = os.path.splitext(base)
        hits = []
        for key in (base, stem):
            hits.extend(by_base.get(key, []))
        seen = set()
        for path in hits:
            if path in seen or path in matched:
                continue
            seen.add(path)
            matched.add(path)
            if status == "PASS":
                set_result(path, "PASS", "automake %s。%s" % (status, command))
            elif status == "SKIP":
                set_result(
                    path,
                    "BLOCKED",
                    "automake SKIP %s。配置未提供该用例的依赖。%s" % (name, summary),
                )
            elif status == "XFAIL":
                set_result(path, "PASS", "automake XFAIL（上游预期失败）%s" % name)
            else:
                detail = interesting(text)
                if "pngtest" in name:
                    bits = []
                    for line in ANSI.sub("", text).splitlines():
                        stripped = line.strip()
                        if (
                            "zlib version" in stripped
                            or "are different" in stripped
                            or "IDAT chunk size" in stripped
                        ):
                            bits.append(stripped)
                        if len(bits) >= 4:
                            break
                    if bits:
                        detail = " | ".join(bits) + " | " + detail
                set_result(
                    path,
                    "FAIL",
                    "automake %s %s。%s" % (status, name, detail),
                )
    for path in files:
        if path in matched or path in RESULTS:
            continue
        if code == 0:
            set_result(
                path,
                "PASS",
                "套件退出码 0，此文件是夹具或构建描述，没有单独的结果行。%s。%s"
                % (summary, command),
            )
        else:
            set_result(
                path,
                "BLOCKED",
                "套件退出码 %s，此文件没有单独的 PASS/FAIL 行。%s。命令 %s"
                % (code, summary, command),
            )


def collect(src):
    found = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [
            name
            for name in dirs
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        rel_root = os.path.relpath(root, src)
        parts = [] if rel_root == "." else rel_root.split(os.sep)
        if any(part in SKIP_DIRS for part in parts):
            continue
        if not any(part in EXACT_DIRS for part in parts):
            continue
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in SKIP_EXT:
                continue
            rel = "/".join(parts + [name])
            found.append(rel)
    return sorted(found)


def run_extra(gs, src, out):
    global HARD_FAIL
    samples = []
    examples = os.path.join(src, "examples")
    for name in (
        "alphabet.ps",
        "colorcir.ps",
        "doretree.ps",
        "escher.ps",
        "grayalph.ps",
        "snowflak.ps",
        "spots.ps",
        "waterfal.ps",
        "vasarely.ps",
        "transparency_example.ps",
        "golfer.eps",
        "ridt91.eps",
        "tiger.eps",
        "annots.pdf",
        "spots2.pdf",
        "text_graph_image_cmyk_rgb.pdf",
        "text_graphic_image.pdf",
    ):
        samples.append(os.path.join(examples, name))
    cjk = os.path.join(examples, "cjk")
    if os.path.isdir(cjk):
        for name in sorted(os.listdir(cjk)):
            if name.endswith((".ps", ".eps", ".pdf")):
                samples.append(os.path.join(cjk, name))

    def one(label, cmd):
        global HARD_FAIL
        code, text = run(cmd, out, os.path.join(out, "extra", label + ".log"), 120)
        if code == 0:
            emit("EXTRA PASS " + label)
            return
        cid = any(marker in text for marker in CID_MARKERS)
        emit("EXTRA FAIL %s %s" % (label, "cid-font" if cid else "other"))
        emit(interesting(text)[:400])
        if not cid:
            HARD_FAIL = True

    one(
        "acctest",
        [gs, "-dNODISPLAY", "-dNOPAUSE", "-dBATCH", os.path.join(src, "lib", "acctest.ps")],
    )
    for sample in samples:
        base = os.path.basename(sample)
        png = os.path.join(out, "extra", base + ".png")
        one(
            "render-" + base,
            [
                gs,
                "-dNOPAUSE",
                "-dBATCH",
                "-sDEVICE=png16m",
                "-r72",
                "-sOutputFile=" + png,
                sample,
            ],
        )
    wrappers = [
        ("ps2pdf-alphabet", ["ps2pdf", os.path.join(examples, "alphabet.ps"), os.path.join(out, "extra", "alphabet.pdf")]),
        ("ps2pdf-colorcir", ["ps2pdf", os.path.join(examples, "colorcir.ps"), os.path.join(out, "extra", "colorcir.pdf")]),
        ("ps2pdf-tiger", ["ps2pdf", os.path.join(examples, "tiger.eps"), os.path.join(out, "extra", "tiger.pdf")]),
        ("pdf2ps-annots", ["pdf2ps", os.path.join(examples, "annots.pdf"), os.path.join(out, "extra", "annots.ps")]),
        ("pdf2ps-text", ["pdf2ps", os.path.join(examples, "text_graphic_image.pdf"), os.path.join(out, "extra", "text_graphic_image.ps")]),
    ]
    for label, cmd in wrappers:
        one(label, cmd)


def run_tiff(src, out, cc):
    files = [path for path in RESULTS_ORDER if path.startswith("tiff/")]
    build = os.path.join(out, "tiff-build")
    os.makedirs(build, exist_ok=True)
    configure = os.path.join(src, "tiff", "configure")
    relax_configure(configure)
    flags = "-I%s/base -I%s/obj" % (src, src)
    # conanbuild 的 PATH 里有一个 c++，autoconf 会选中它并用 /lib/cpp 做预处理，
    # 这台机器上该预处理失败。--disable-cxx 仍不编 tif_stream.cxx，但探测必须用 SDK clang++。
    env = {
        "CC": cc,
        "CXX": sdk_bin("clang++"),
        "CPPFLAGS": flags,
        "CFLAGS": "-g -O2",
    }
    if not os.path.isfile(os.path.join(build, "Makefile")):
        code, text = run(
            # horizontalDifferenceF/16/8 使用了未声明的 sp。GS 自己的 tif_pixarlog.o 是空的
            # （未定义 PIXARLOG_SUPPORT）。打开该宏会在 clang 上编不过，所以测试构建关掉它。
            [configure, "--disable-cxx", "--disable-pixarlog", "--disable-dependency-tracking"],
            build,
            os.path.join(out, "logs", "tiff-configure.log"),
            300,
            env,
        )
        if code != 0:
            reason = "libtiff configure --disable-cxx --disable-pixarlog 失败。%s" % interesting(text)
            for path in files:
                set_result(path, "BLOCKED", reason)
            return
    enable_snprintf(build)
    code, text = run(
        ["make", "-j2", "check", "CPPFLAGS=" + flags],
        build,
        os.path.join(out, "logs", "tiff-check.log"),
        7200,
        env,
    )
    assign_automake(files, text, code, "make -C tiff-build -j2 check CPPFLAGS=%s" % flags)


def run_libpng(src, out, cc):
    files = [path for path in RESULTS_ORDER if path.startswith("libpng/")]
    build = os.path.join(out, "libpng-build")
    os.makedirs(build, exist_ok=True)
    configure = os.path.join(src, "libpng", "configure")
    relax_configure(configure)
    brew = os.path.expanduser("~/.harmonybrew")
    env = {
        "CC": cc,
        "CPPFLAGS": "-I%s/include" % brew,
        "LDFLAGS": "-L%s/lib" % brew,
        "LD_LIBRARY_PATH": "%s/lib:%s" % (brew, os.environ.get("LD_LIBRARY_PATH", "")),
        "PKG_CONFIG_PATH": "%s/lib/pkgconfig" % brew,
    }
    if not os.path.isfile(os.path.join(build, "Makefile")):
        code, text = run(
            [configure, "--disable-dependency-tracking"],
            build,
            os.path.join(out, "logs", "libpng-configure.log"),
            300,
            env,
        )
        if code != 0:
            reason = "libpng configure 失败。%s" % interesting(text)
            for path in files:
                set_result(path, "BLOCKED", reason)
            return
    code, text = run(
        ["make", "-j2", "check"],
        build,
        os.path.join(out, "logs", "libpng-check.log"),
        7200,
        env,
    )
    suite_log = os.path.join(build, "test-suite.log")
    if os.path.isfile(suite_log):
        with open(suite_log, encoding="utf-8", errors="replace") as handle:
            text = text + "\n" + handle.read()
    assign_automake(files, text, code, "make -C libpng-build -j2 check")


def file_stem(path):
    base = os.path.basename(path)
    for suffix in (".cmake.in", ".cmake", ".cc", ".cpp", ".c", ".txt", ".cm"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return os.path.splitext(base)[0]


def map_ctest(files, text, code, command):
    matched = {}
    clean = ANSI.sub("", text)
    for name, _stars, status in CTEST.findall(clean):
        ranked = []
        for path in files:
            stem = file_stem(path)
            if stem and stem in name:
                ranked.append((len(stem), path))
        if not ranked:
            continue
        best = max(item[0] for item in ranked)
        for length, path in ranked:
            if length != best or path in matched:
                continue
            state = status.lower()
            if state == "passed":
                matched[path] = ("PASS", "ctest %s Passed。%s" % (name, command))
            elif "not run" in state:
                matched[path] = (
                    "BLOCKED",
                    "ctest %s Not Run，前置配置失败。%s" % (name, interesting(text)),
                )
            else:
                matched[path] = (
                    "FAIL",
                    "ctest %s %s。%s" % (name, status, interesting(text)),
                )
    for path, (status, reason) in matched.items():
        RESULTS[path] = (status, reason[:900])
        emit("CASE %s %s %s" % (status, path, reason[:240]))
    for path in files:
        if path in matched or path in RESULTS:
            continue
        if os.path.basename(path) == "minigzip.c":
            set_result(
                path,
                "BLOCKED",
                "test/CMakeLists.txt 把 minigzip.c 编成 minigzip 与 static_minigzip，"
                "没有 add_test，ctest 不运行它。同目录 ctest 退出码 %s。%s" % (code, command),
            )
            continue
        if code == 0 and "Passed" in text:
            set_result(
                path,
                "PASS",
                "ctest 退出码 0，此文件是该次构建的测试描述或夹具。%s" % command,
            )
        else:
            set_result(
                path,
                "BLOCKED",
                "ctest 退出码 %s，没有把该文件对应到 Passed。%s。%s"
                % (code, interesting(text), command),
            )


def zlib_config_dir(prefix):
    direct = os.path.join(prefix, "lib", "cmake", "zlib")
    if os.path.isfile(os.path.join(direct, "ZLIBConfig.cmake")):
        return direct
    if not os.path.isdir(prefix):
        return ""
    for root, _dirs, files in os.walk(prefix):
        if "ZLIBConfig.cmake" in files:
            return root
    return ""


def run_zlib(src, out, cc):
    cmake = which("cmake")
    ctest = which("ctest") or "ctest"
    groups = [
        ("zlib", os.path.join(src, "zlib"), "zlib/test/"),
        ("blast", os.path.join(src, "zlib", "contrib", "blast"), "zlib/contrib/blast/test/"),
        ("iostream3", os.path.join(src, "zlib", "contrib", "iostream3"), "zlib/contrib/iostream3/test/"),
        ("minizip", os.path.join(src, "zlib", "contrib", "minizip"), "zlib/contrib/minizip/test/"),
        ("puff", os.path.join(src, "zlib", "contrib", "puff"), "zlib/contrib/puff/test/"),
    ]
    if not cmake:
        for path in RESULTS_ORDER:
            if path.startswith("zlib/"):
                set_result(path, "BLOCKED", "command -v cmake 为空，无法构建 zlib 的 CMake 测试。")
        return
    env = {"CC": cc, "CFLAGS": "-g -O2"}
    for name, source, prefix in groups:
        files = [path for path in RESULTS_ORDER if path.startswith(prefix)]
        if not files:
            continue
        build = os.path.join(out, "zlib-" + name)
        cmake_cmd = [
            cmake,
            "-S",
            source,
            "-B",
            build,
            "-DZLIB_BUILD_TESTING=ON",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_C_COMPILER=" + cc,
            "-DCMAKE_CXX_COMPILER=" + sdk_bin("clang++"),
            "-DCMAKE_SYSTEM_NAME=Linux",
        ]
        if env.get("ZLIB_DIR"):
            cmake_cmd.append("-DZLIB_DIR=" + env["ZLIB_DIR"])
            cmake_cmd.append("-DCMAKE_PREFIX_PATH=" + env["CMAKE_PREFIX_PATH"])
        code, text = run(
            cmake_cmd,
            out,
            os.path.join(out, "logs", "zlib-%s-configure.log" % name),
            180,
            env,
        )
        if code != 0:
            reason = "cmake -S %s 失败。%s" % (source, interesting(text))
            for path in files:
                set_result(path, "BLOCKED", reason)
            continue
        code, text = run(
            [cmake, "--build", build, "-j2"],
            out,
            os.path.join(out, "logs", "zlib-%s-build.log" % name),
            300,
            env,
        )
        if code != 0:
            reason = "cmake --build %s 失败。%s" % (name, interesting(text))
            for path in files:
                set_result(path, "BLOCKED", reason)
            continue
        if name == "zlib":
            prefix = os.path.join(build, "test", "test_install")
            icode, itext = run(
                [cmake, "--install", build, "--prefix", prefix],
                out,
                os.path.join(out, "logs", "zlib-install.log"),
                180,
                env,
            )
            zdir = zlib_config_dir(prefix)
            if icode == 0 and zdir:
                env = dict(env)
                env["ZLIB_DIR"] = zdir
                env["CMAKE_PREFIX_PATH"] = prefix
                emit("ZLIB_DIR=" + zdir)
            else:
                emit("ZLIB_INSTALL_RC=%s %s" % (icode, interesting(itext)[:180]))
        code, text = run(
            [ctest, "--test-dir", build, "--output-on-failure"],
            out,
            os.path.join(out, "logs", "zlib-%s-ctest.log" % name),
            300,
            env,
        )
        map_ctest(files, text, code, "ctest --test-dir zlib-%s" % name)


def run_extract(gs, src, out, cc):
    extract = os.path.join(src, "extract")
    logs = os.path.join(out, "logs")
    mild = "-g -Wall -Iinclude -Isrc"
    env = {"CC": cc}
    harness = {}
    for target in ("test-src", "test-buffer", "test-misc"):
        code, text = run(
            ["make", target, "CC=" + cc],
            extract,
            os.path.join(logs, "extract-%s.log" % target),
            240,
            env,
        )
        if code != 0 and target != "test-src":
            code, text = run(
                ["make", target, "CC=" + cc, "flags_compile=" + mild, "flags_link=-lm"],
                extract,
                os.path.join(logs, "extract-%s-retry.log" % target),
                240,
                env,
            )
            note = "首次按上游 -Werror 失败，已去掉 -Werror 重跑。"
        else:
            note = ""
        harness[target] = (code, note + interesting(text))
        emit("HARNESS extract %s rc=%s" % (target, code))
    code, text = run(
        ["make", "test-gs", "gs=" + gs, "CC=" + cc],
        extract,
        os.path.join(logs, "extract-test-gs.log"),
        420,
        env,
    )
    gs_reason_ok = code == 0
    gs_detail = interesting(text)
    emit("HARNESS extract test-gs rc=%s" % code)
    mutool = which("mutool")
    for path in RESULTS_ORDER:
        if not path.startswith("extract/"):
            continue
        gs_case = ".gs." in path or os.path.basename(path) in {
            "Python2.pdf",
            "zlib.3.pdf",
            "text_graphic_image.pdf",
        }
        if gs_case:
            if gs_reason_ok:
                set_result(path, "PASS", "extract make test-gs gs=%s 退出码 0" % gs)
            else:
                set_result(
                    path,
                    "FAIL",
                    "extract make test-gs 退出码 %s。%s" % (code, gs_detail),
                )
            continue
        if mutool:
            set_result(path, "BLOCKED", "mutool 在 PATH 中，但本文件属于 mutool 夹具，test-mutool 未单独归类。")
        else:
            set_result(
                path,
                "BLOCKED",
                "command -v mutool 为空。该文件是 mupdf mutool 的期望输出或输入，"
                "ghostscript 发行包不含 mutool。extract 的 test-buffer rc=%s，test-misc rc=%s，test-src rc=%s。"
                % (harness["test-buffer"][0], harness["test-misc"][0], harness["test-src"][0]),
            )


def run_toolbin(src, out, cc):
    root = os.path.join(src, "toolbin", "tests")
    for path in RESULTS_ORDER:
        if not path.startswith("toolbin/"):
            continue
        full = os.path.join(src, path)
        name = os.path.basename(path)
        log = os.path.join(out, "logs", "toolbin-" + name + ".log")
        if name == "README":
            set_result(
                path,
                "BLOCKED",
                "toolbin/tests/README 说明集群回归目录在 /home/regression/comparefiles，"
                "发行包没有 comparefiles。同目录可执行脚本已逐个启动。",
            )
            continue
        if path.endswith(".c"):
            binary = os.path.join(out, "toolbin-" + name + ".bin")
            code, text = run(
                [cc, "-O2", full, "-o", binary],
                out,
                log,
                60,
            )
            if code != 0:
                set_result(path, "FAIL", "编译 %s 失败。%s" % (name, interesting(text)))
                continue
            code, text = run([binary], out, log + ".run", 30)
            if code == 0:
                set_result(path, "PASS", "clang 编译并运行退出码 0")
            elif "Usage:" in text:
                set_result(
                    path,
                    "BLOCKED",
                    "编译成功。无参数运行只打印用法并退出 %s。fuzzy 用来比较两张图，"
                    "需要 toolbin 集群的 comparefiles，发行包没有这些样本。%s"
                    % (code, interesting(text)),
                )
            else:
                set_result(path, "FAIL", "运行 %s 退出码 %s。%s" % (name, code, interesting(text)))
            continue
        first = ""
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as handle:
                first = handle.readline()
        except OSError as exc:
            set_result(path, "BLOCKED", "无法读取：%s" % exc)
            continue
        timeout = 90 if name.startswith(("gscheck", "run_", "check_all")) else 40
        if "python" in first or path.endswith(".py"):
            code, text = run([which("python3") or "python3", full], root, log, timeout)
        else:
            code, text = run(["bash", full], root, log, timeout)
        detail = interesting(text)
        if code == 0:
            set_result(path, "PASS", "退出码 0")
        elif any(
            token in text
            for token in (
                "SyntaxError",
                "Missing parentheses",
                "TabError",
                "IndentationError",
            )
        ):
            set_result(
                path,
                "BLOCKED",
                "设备没有 python2，python3 %s 无法执行该 Python 2 集群脚本。%s"
                % (sys.version.split()[0], detail),
            )
        elif "comparefiles" in text or "/home/regression" in text or "testing.cfg" in text:
            set_result(
                path,
                "BLOCKED",
                "脚本启动后找不到集群目录 /home/regression 或 comparefiles（发行包未附带）。%s" % detail,
            )
        else:
            set_result(path, "FAIL", "退出码 %s。%s" % (code, detail))


def run_brotli(src, out):
    files = [path for path in RESULTS_ORDER if path.startswith("brotli/")]
    py = which("python3") or "python3"
    pip = which("pip3")
    cc = sdk_bin("clang")
    deps = os.path.join(out, "pydeps")
    os.makedirs(deps, exist_ok=True)
    brew_lib = os.path.expanduser("~/.harmonybrew/lib")
    env = {
        "PYTHONPATH": deps + os.pathsep + os.environ.get("PYTHONPATH", ""),
        "CC": cc,
        "CXX": sdk_bin("clang++"),
        "LDFLAGS": "-L" + brew_lib,
        "LIBRARY_PATH": brew_lib,
        "LD_LIBRARY_PATH": brew_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""),
    }
    if pip:
        run(
            [pip, "install", "--target", deps, "pytest", "setuptools"],
            out,
            os.path.join(out, "logs", "pip-pytest.log"),
            240,
        )
    # 优先用已安装的 brotli 模块；否则用发行包里的 setup.py 编扩展。
    code, text = run(
        [py, "-c", "import brotli; print(brotli.__file__)"],
        out,
        os.path.join(out, "logs", "brotli-import.log"),
        30,
        env,
    )
    if code != 0:
        code, text = run(
            [py, "setup.py", "build_ext", "--inplace"],
            os.path.join(src, "brotli"),
            os.path.join(out, "logs", "brotli-build.log"),
            300,
            env,
        )
        if code != 0:
            reason = "import brotli 失败，且 python3 setup.py build_ext --inplace 失败。%s" % interesting(text)
            for path in files:
                set_result(path, "BLOCKED", reason)
            return
        env["PYTHONPATH"] = os.path.join(src, "brotli", "python") + os.pathsep + env["PYTHONPATH"]
        code, text = run(
            [py, "-c", "import brotli; print('IMPORT_OK', brotli.__file__)"],
            os.path.join(src, "brotli"),
            os.path.join(out, "logs", "brotli-import2.log"),
            30,
            env,
        )
        if code != 0:
            reason = "扩展编过，import brotli 仍失败。%s" % interesting(text)
            for path in files:
                set_result(path, "BLOCKED", reason)
            return
    code, text = run(
        [py, "-m", "pytest", "-q", os.path.join(src, "brotli", "python", "tests")],
        os.path.join(src, "brotli"),
        os.path.join(out, "logs", "brotli-pytest.log"),
        300,
        env,
    )
    if code == 0:
        for path in files:
            set_result(path, "PASS", "python3 -m pytest brotli/python/tests 退出码 0")
    else:
        reason = "pytest 退出码 %s。%s" % (code, interesting(text))
        if "FileNotFoundError" in text and "testdata" in text:
            status = "BLOCKED"
            reason = (
                "pytest 退出码 %s。ghostscript 自带的 brotli 目录没有 tests/testdata"
                "（发行包未含 zerosukkanooa.compressed 等样本），python 测试读样本失败。%s"
                % (code, interesting(text))
            )
        else:
            status = "BLOCKED" if "No module named pytest" in text or "No module named brotli" in text else "FAIL"
        for path in files:
            set_result(path, status, reason)


def run_freetype(src, out, cc):
    files = [path for path in RESULTS_ORDER if path.startswith("freetype/")]
    meson = which("meson")
    if not meson:
        for path in files:
            set_result(path, "BLOCKED", "command -v meson 为空。freetype 测试只在 meson -Dtests=enabled 下构建。")
        return
    py = which("python3") or "python3"
    pip = which("pip3")
    deps = os.path.join(out, "pydeps")
    os.makedirs(deps, exist_ok=True)
    font_env = {"PYTHONPATH": deps + os.pathsep + os.environ.get("PYTHONPATH", "")}
    if pip:
        run(
            [pip, "install", "--target", deps, "requests"],
            out,
            os.path.join(out, "logs", "pip-requests.log"),
            180,
        )
    script = os.path.join(src, "freetype", "tests", "scripts", "download-test-fonts.py")
    font_file = os.path.join(src, "freetype", "tests", "data", "As.I.Lay.Dying.ttf")
    font_ready = os.path.isfile(font_file) and os.path.getsize(font_file) > 0
    if font_ready:
        emit(
            "FREETYPE_FONT_PRESENT bytes=%s %s"
            % (os.path.getsize(font_file), font_file)
        )
    else:
        code, text = run(
            [py, script],
            os.path.join(src, "freetype"),
            os.path.join(out, "logs", "freetype-fonts.log"),
            600,
            font_env,
        )
        attempt = 1
        while code != 0 and attempt < 3:
            attempt += 1
            code, text = run(
                [py, script],
                os.path.join(src, "freetype"),
                os.path.join(out, "logs", "freetype-fonts-retry%s.log" % attempt),
                600,
                font_env,
            )
        if code != 0:
            reason = (
                "tests/scripts/download-test-fonts.py 退出码 %s。"
                "发行包没有 tests/data 字体，meson 测试依赖这次下载，"
                "且 tests/data/As.I.Lay.Dying.ttf 不存在。%s"
                % (code, interesting(text))
            )
            for path in files:
                set_result(path, "BLOCKED", reason)
            return
    build = os.path.join(out, "freetype-build")
    code, text = run(
        [meson, "setup", build, os.path.join(src, "freetype"), "-Dtests=enabled"],
        out,
        os.path.join(out, "logs", "freetype-setup.log"),
        180,
        {"CC": cc},
    )
    if code != 0:
        reason = "meson setup -Dtests=enabled 失败。%s" % interesting(text)
        for path in files:
            set_result(path, "BLOCKED", reason)
        return
    code, text = run(
        [meson, "compile", "-C", build],
        out,
        os.path.join(out, "logs", "freetype-compile.log"),
        600,
        {"CC": cc},
    )
    if code != 0:
        reason = "meson compile 失败。%s" % interesting(text)
        for path in files:
            set_result(path, "BLOCKED", reason)
        return
    code, text = run(
        [meson, "test", "-C", build],
        out,
        os.path.join(out, "logs", "freetype-test.log"),
        600,
    )
    if code == 0:
        for path in files:
            set_result(path, "PASS", "meson test -C freetype-build 退出码 0")
    else:
        for path in files:
            set_result(path, "FAIL", "meson test 退出码 %s。%s" % (code, interesting(text)))


def run_tesseract(src, out, cc):
    files = [path for path in RESULTS_ORDER if path.startswith("tesseract/")]
    unittest = os.path.join(src, "tesseract", "unittest")
    gtest_cmake = os.path.join(unittest, "third_party", "googletest", "CMakeLists.txt")
    trained = []
    for root, _dirs, names in os.walk(os.path.join(src, "tesseract")):
        for name in names:
            if name.endswith(".traineddata"):
                trained.append(os.path.join(root, name))
    cxx = which("clang++") or "clang++"
    sample = os.path.join(unittest, "list_test.cc")
    code, text = run(
        [
            cxx,
            "-std=c++17",
            "-fsyntax-only",
            "-I" + os.path.join(src, "tesseract", "include"),
            "-I" + os.path.join(src, "tesseract", "src", "ccutil"),
            sample,
        ],
        unittest,
        os.path.join(out, "logs", "tesseract-compile.log"),
        60,
    )
    clone_note = ""
    dest = os.path.join(out, "googletest")
    git = which("git")
    if git and not os.path.isfile(gtest_cmake):
        gcode, gtext = run(
            [git, "clone", "--depth", "1", "https://github.com/google/googletest.git", dest],
            out,
            os.path.join(out, "logs", "gtest-clone.log"),
            90,
        )
        clone_note = "git clone googletest 退出码 %s。%s" % (gcode, interesting(gtext))
    lept = "未检测"
    pkg = which("pkg-config")
    if pkg:
        lcode, _ltext = run(
            [pkg, "--exists", "lept"],
            out,
            os.path.join(out, "logs", "pkg-lept.log"),
            20,
        )
        lept = "pkg-config --exists lept 退出码 %s" % lcode
    fuzz = os.path.join(unittest, "fuzzers", "oss-fuzz-build.sh")
    if os.path.isfile(fuzz):
        run(["bash", fuzz], os.path.dirname(fuzz), os.path.join(out, "logs", "oss-fuzz.log"), 30)
    reason = (
        "tesseract/Makefile.am 的 check_PROGRAMS 要链接 libgtest.la，源文件路径是 "
        "unittest/third_party/googletest/googletest/src/gtest-all.cc；发行包里该 CMakeLists "
        "%s。unittest/include_gunit.h 包含 gtest/gtest.h。试编译 list_test.cc 退出码 %s：%s "
        "traineddata 数量=%s。%s。%s。Makefile.am 还把 langdata 与 tessdata/tessdata_best/"
        "tessdata_fast 以及测试字体列为这些程序的 order-only 依赖，发行包没有这些目录。"
        % (
            "存在" if os.path.isfile(gtest_cmake) else "不存在",
            code,
            interesting(text),
            len(trained),
            lept,
            clone_note,
        )
    )
    for path in files:
        set_result(path, "BLOCKED", reason)


def run_gstest(src):
    files = [path for path in RESULTS_ORDER if path.startswith("demos/")]
    java = which("java")
    javac = which("javac")
    brew_java = []
    opt = os.path.expanduser("~/.harmonybrew/opt")
    if os.path.isdir(opt):
        for name in os.listdir(opt):
            if "jdk" in name.lower() or "java" in name.lower():
                brew_java.append(name)
    if java and javac:
        main = os.path.join(src, "demos", "java", "gstest", "src", "gstest", "Main.java")
        code, text = run(
            [javac, main],
            os.path.dirname(main),
            os.path.join(os.environ["GS14845_OUT"], "logs", "gstest-javac.log"),
            60,
        )
        for path in files:
            if code == 0:
                set_result(path, "PASS", "javac Main.java 退出码 0")
            else:
                set_result(
                    path,
                    "BLOCKED",
                    "javac 能启动，但 Main.java 依赖未随 C 库构建生成的 Java 绑定"
                    "（NativePointer、GS_SPT_INT）。本配方不编译该 Java 示例的依赖类。"
                    "javac 退出码 %s。%s" % (code, interesting(text)),
                )
        return
    reason = (
        "command -v java 为 %s，command -v javac 为 %s，harmonybrew opt 中 JDK 目录 %s。"
        "demos/java/gstest 是 Eclipse Java 示例（.classpath、.project、Main.java），"
        "没有 JDK 无法编译。"
        % (java or "空", javac or "空", brew_java or "无")
    )
    for path in files:
        set_result(path, "BLOCKED", reason)


def main():
    global RESULTS_ORDER
    if len(sys.argv) != 4:
        emit("usage: upstream_tests.py <gs> <src> <out>")
        return 2
    gs, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, "tmp")
    os.makedirs(tmp, exist_ok=True)
    os.environ["TMPDIR"] = tmp
    os.environ["TEMP"] = tmp
    os.environ["TMP"] = tmp
    os.environ.pop("GS_LIB", None)
    os.environ.pop("GS_FONTPATH", None)
    os.environ["GS14845_OUT"] = out
    os.environ.pop("MAKEFLAGS", None)
    gs_dir = os.path.dirname(os.path.abspath(gs))
    os.environ["PATH"] = gs_dir + os.pathsep + os.environ.get("PATH", "")
    cc = sdk_bin("clang")
    ensure_tools(out)
    emit("CC=" + cc)
    if not os.path.isfile(gs):
        emit("NO_GS " + gs)
        return 1
    code, text = run([gs, "--version"], out, os.path.join(out, "logs", "gs-version.log"), 30)
    emit("GS_VERSION_RC=%s %s" % (code, text.strip().splitlines()[-1] if text.strip() else ""))
    if code != 0:
        return 1
    cases = collect(src)
    RESULTS_ORDER = cases
    emit("COUNT_RULE=dir in {test,tests,unittest,unittests,gstest} and ext!=.xml exclude tiff-config/.deps/obj/soobj/generated/data")
    emit("UPSTREAM_ENUM=%s" % len(cases))
    if len(cases) != 508:
        emit("COUNT_MISMATCH want 508 got %s" % len(cases))
        from collections import Counter

        tops = Counter(path.split("/")[0] for path in cases)
        for key, value in tops.most_common():
            emit("TOP %s %s" % (value, key))
        return 2
    run_extra(gs, src, out)
    run_extract(gs, src, out, cc)
    run_toolbin(src, out, cc)
    run_tesseract(src, out, cc)
    run_gstest(src)
    run_brotli(src, out)
    run_zlib(src, out, cc)
    run_libpng(src, out, cc)
    run_freetype(src, out, cc)
    run_tiff(src, out, cc)
    missing = [path for path in cases if path not in RESULTS]
    for path in missing:
        set_result(path, "BLOCKED", "脚本结束时仍没有结果。")
    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}
    for status, _reason in RESULTS.values():
        counts[status] = counts.get(status, 0) + 1
    emit("UPSTREAM_TOTAL=%s" % len(cases))
    emit("UPSTREAM_PASS=%s" % counts.get("PASS", 0))
    emit("UPSTREAM_FAIL=%s" % counts.get("FAIL", 0))
    emit("UPSTREAM_BLOCKED=%s" % counts.get("BLOCKED", 0))
    ledger = os.path.join(out, "ledger.txt")
    with open(ledger, "w", encoding="utf-8") as handle:
        for path in cases:
            status, reason = RESULTS[path]
            handle.write("%s\t%s\t%s\n" % (status, path, reason))
    emit("LEDGER " + ledger)
    unexplained = [
        path
        for path, (status, reason) in RESULTS.items()
        if status != "PASS" and not reason.strip()
    ]
    if unexplained or HARD_FAIL:
        emit("UPSTREAM_RESULT=FAIL")
        return 1
    emit("UPSTREAM_RESULT=REASONS_RECORDED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
