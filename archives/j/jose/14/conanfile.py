import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, chmod, copy,
                               export_conandata_patches, get, replace_in_file)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


def _newest(paths):
    for path in sorted(paths, reverse=True):
        if os.path.isfile(path):
            return path
    return ""


def _find_binutil(name):
    """Locate an LLVM/OHOS binutil on both the CI worker and the true machine.

    The worker keeps them in /data/service/hnp/bin; on the device they live
    inside the versioned harmonybrew ohos-sdk bottle, so the directory cannot
    be hard-coded (same finding as proj/9.8.1).
    """
    found = shutil.which(name)
    if found:
        return found
    home = os.path.expanduser("~")
    cands = [os.path.join("/data/service/hnp/bin", name)]
    for pattern in ("*/native/llvm/bin", "*/bin", "*/toolchains/lib",
                    "*/toolchains"):
        for root in glob.glob(os.path.join(home, ".harmonybrew", "opt", pattern)):
            cands.append(os.path.join(root, name))
    return _newest(cands)


def _resign_elf(path, objcopy, signer):
    """Strip the stale .codesign section and self-sign one ELF file (E077).

    `meson install` rewrites DT_RUNPATH in the installed copy, which
    invalidates the signature the linker had added; OHOS musl then refuses to
    exec or dlopen the packaged file. Returns True only when the file was
    actually re-signed.
    """
    if os.path.islink(path):
        return False
    try:
        with open(path, "rb") as handle:
            if handle.read(4) != b"\x7fELF":
                return False
    except OSError:
        return False

    work = path + ".nosig"
    shutil.copy2(path, work)
    strip = subprocess.run([objcopy, "--remove-section", ".codesign", work],
                           capture_output=True)
    sign = None
    if strip.returncode == 0:
        sign = subprocess.run([signer, "sign", "-inFile", work,
                               "-outFile", path, "-selfSign", "1"],
                              capture_output=True)
    if os.path.exists(work):
        os.remove(work)
    if sign is None or sign.returncode != 0:
        return False
    os.chmod(path, 0o755)
    return True


class JoseConan(ConanFile):
    name = "jose"
    version = "14"
    description = ("JOSE (JSON Object Signing and Encryption) implementation "
                   "in C: JWK/JWS/JWE library plus the `jose` command line tool")
    license = "APL2"
    homepage = "https://github.com/latchset/jose"
    url = ""  # CI fills this
    topics = ("jose", "jwk", "jws", "jwe", "crypto")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # jansson 是真实的公开依赖：libjose.so.0 的 DT_NEEDED 里有
        # libjansson.so，且公共头 jose/jwk.h 直接 include <jansson.h>。
        self.requires("jansson/2.15.1.1", transitive_headers=True,
                      transitive_libs=True)
        # openssl 与 zlib 制品仓只有静态库，编译期被整体吸收进 libjose.so.0
        # （实测该 .so 的 DT_NEEDED 只有 libjansson.so 与 libc.so），因此是
        # 私有依赖：标 visible=False，既不让消费者重复链接，也不会在
        # package_info 的 requires 收窄时被判成「未使用的直接依赖」。
        self.requires("openssl/3.5.8.1", visible=False)
        self.requires("zlib/1.3.1.1", visible=False)

    def build_requirements(self):
        # The device's harmonybrew provides ninja but no meson, while the CI
        # worker has meson on PATH; pinning the tool makes both sides agree.
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload 的 URL 末段是 tag 名、没有 .tar.gz 后缀，conan 会按后缀猜
        # 解包类型而误判成 zip（BadZipFile），因此显式给文件名。
        get(self, filename="jose-14.tar.gz", **self.conan_data["sources"],
            strip_root=True)

    # ------------------------------------------------------------------ #
    # generate
    # ------------------------------------------------------------------ #

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_openssl_aliases()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static")
        # a2x is absent on OHOS, so the asciidoc man pages cannot be built.
        tc.project_options["docs"] = "disabled"
        # Upstream defaults to werror=true plus warning_level=2; clang 15
        # turns its own -Wshadow/-Wstrict-prototypes findings into errors.
        tc.project_options["werror"] = "false"
        # Upstream keeps every test side effect inside assert(...) (feed(),
        # done(), gen()). Release adds -DNDEBUG, assert() becomes ((void)0)
        # and the suite would "pass" having executed nothing. Keep asserts.
        tc.project_options["b_ndebug"] = "false"
        # No subprojects/wrap downloads at build time.
        tc.project_options["wrap_mode"] = "nodownload"
        self._inject_binaries(tc)
        tc.generate()

        self._export_build_env()

    def _write_openssl_aliases(self):
        """Add libcrypto.pc/libssl.pc for upstream's dependency('libcrypto').

        PkgConfigDeps names the generated file after the Conan package
        (openssl.pc), but jose's lib/meson.build asks for `libcrypto` and
        tests/issue-75 for `openssl`. Derive the aliases from the generated
        openssl.pc and keep every -L/rpath flag from its Libs line, otherwise
        ld.lld reports "unable to find library -lcrypto".
        """
        source_pc = os.path.join(self.generators_folder, "openssl.pc")
        if not os.path.isfile(source_pc):
            self.output.warning("openssl.pc not generated; skipping aliases")
            return
        with open(source_pc, encoding="utf-8") as handle:
            content = handle.read()
        search = " ".join(re.findall(
            r"(?:-L|-Wl,-rpath,|-R|--library-path=)\S+", content)).strip()
        for name, libs in (("libcrypto.pc", "-lcrypto"),
                           ("libssl.pc", "-lssl -lcrypto")):
            alias = re.sub(r"^Name:.*$", "Name: %s" % name[:-3],
                           content, flags=re.M)
            alias = re.sub(r"^Libs:.*$",
                           "Libs: %s" % ((search + " " + libs).strip() or libs),
                           alias, flags=re.M)
            with open(os.path.join(self.generators_folder, name), "w",
                      encoding="utf-8") as handle:
                handle.write(alias)

    def _inject_binaries(self, tc):
        """Pin the whole LLVM tool chain for meson.

        The OHOS profile only lists the compilers in
        tools.build:compiler_executables; meson then probes bare `llvm-ar`,
        `llvm-nm`, ... on PATH, which fails on the device because CPython
        spawns them through posix_spawn without a PATH lookup.
        """
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        cc = executables.get("c") or ""
        bindir = os.path.dirname(os.path.realpath(cc)) if cc else ""
        if cc and os.path.isfile(cc):
            tc.binaries["c"] = cc
        cpp = executables.get("cpp") or (
            os.path.join(bindir, "clang++") if bindir else "")
        if cpp and os.path.isfile(cpp):
            tc.binaries["cpp"] = cpp
        for key, tool in (("ar", "llvm-ar"), ("ranlib", "llvm-ranlib"),
                          ("nm", "llvm-nm"), ("strip", "llvm-strip"),
                          ("ld", "ld.lld")):
            path = (os.path.join(bindir, tool) if bindir else "")
            if not (path and os.path.isfile(path)):
                path = _find_binutil(tool)
            if path:
                tc.binaries[key] = path

    def _export_build_env(self):
        """Feed meson an absolute ninja and a writable temporary directory.

        /tmp is read-only on the true machine, and meson resolves ninja by
        name unless $NINJA points at an existing file.
        """
        env = Environment()
        ninja = os.environ.get("NINJA") or _find_binutil("ninja")
        if ninja and os.path.isfile(ninja):
            env.define("NINJA", os.path.realpath(ninja))
        tmpdir = self.build_folder
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.define(var, tmpdir)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("jose_build_env")

    # ------------------------------------------------------------------ #
    # build
    # ------------------------------------------------------------------ #

    def build(self):
        apply_conandata_patches(self)
        self._adapt_upstream_tests()
        meson = Meson(self)
        meson.configure()
        self._force_live_assertions()
        meson.build()
        self._run_upstream_tests()

    def _force_live_assertions(self):
        """Pin b_ndebug=false after configure, then prove it took effect.

        b_ndebug is a meson *built-in* option. MesonToolchain puts what the
        recipe asks for into the machine file, but conan also passes
        --buildtype=release on the setup command line, and meson then re-
        derives b_ndebug=true from the build type (measured on the device:
        werror/docs/default_library/wrap_mode all arrived, b_ndebug came out
        true). That matters here more than usual: upstream keeps the entire
        body of each test - `assert(z->feed(...))`, `assert(z->done(...))` -
        inside assert(), so with -DNDEBUG the suite reports green tests that
        executed no assertions at all, and alg_comp dies on the half-run
        stream instead.
        """
        build_dir = self.build_folder
        self.run('meson configure "{}" -Db_ndebug=false'.format(build_dir),
                 env="conanbuild")

        info = os.path.join(build_dir, "hmbs-buildoptions.json")
        self.run('meson introspect "{}" --buildoptions > "{}" 2>&1'.format(
            build_dir, info), env="conanbuild", ignore_errors=True)
        effective = {}
        try:
            with open(info, encoding="utf-8") as handle:
                for entry in json.load(handle):
                    effective[entry.get("name")] = entry.get("value")
        except (OSError, ValueError) as exc:
            raise RuntimeError("cannot verify meson options: %s" % exc)

        for key in ("buildtype", "b_ndebug", "werror", "default_library",
                    "docs"):
            self.output.info("JOSE_MESON_OPTION %s = %r" %
                             (key, effective.get(key)))
        # meson reports b_ndebug as the string "false" (combo option) but
        # werror as a real boolean, so compare on the string form.
        if str(effective.get("b_ndebug")).strip().lower() != "false":
            raise RuntimeError(
                "b_ndebug is %r: upstream assertions would be compiled out "
                "and the test tally would be meaningless" %
                (effective.get("b_ndebug"),))

    def _adapt_upstream_tests(self):
        """Three environment adaptations; no assertion or vector changes.

        1. tests/meson.build: export TMPDIR/TMP/TEMP into the meson test env.
           Twelve of the sixteen shell scripts do `mktemp -d`, which defaults
           to the read-only /tmp.
        2. tests/jose-jwk-pub, tests/jose-jwk-thp: replace `echo $var |` with
           `printf '%s' "$var" |`. Both run under `#!/bin/sh -ex` = mksh,
           whose unquoted word splitting plus bracket-glob expansion mangles
           the JSON key before jose sees it. Byte-exact value, same
           assertions, same exit semantics.
        3. tests/alg_encr.c: (void) the assert-only helper so -Wunused-variable
           cannot error out if a configuration ever drops NDEBUG again.
        """
        applied = []
        tests_dir = os.path.join(self.source_folder, "tests")

        meson_build = os.path.join(tests_dir, "meson.build")
        anchor = "e.set('VECTORS', meson.current_source_dir() + '/vectors')"
        if os.path.isfile(meson_build):
            with open(meson_build, encoding="utf-8") as handle:
                content = handle.read()
            if "JOSE_TMPDIR" in content:
                applied.append("tmpdir(already)")
            elif anchor in content:
                content = content.replace(anchor, anchor + (
                    "\ne.set('JOSE_TMPDIR', meson.current_build_dir())"
                    "\ne.set('TMPDIR', meson.current_build_dir())"
                    "\ne.set('TMP', meson.current_build_dir())"
                    "\ne.set('TEMP', meson.current_build_dir())"), 1)
                with open(meson_build, "w", encoding="utf-8") as handle:
                    handle.write(content)
                applied.append("tmpdir")
            else:
                self.output.warning("meson.build anchor not found")

        pub = os.path.join(tests_dir, "jose-jwk-pub")
        pub_pairs = [
            ('test "`echo $ioct    | jose jwk pub -i-`"',
             'test "`printf \'%s\' \"$ioct\"    | jose jwk pub -i-`"'),
            ('test "`echo $irsa    | jose jwk pub -i-`"',
             'test "`printf \'%s\' \"$irsa\"    | jose jwk pub -i-`"'),
            ('test "`echo $iec     | jose jwk pub -i-`"',
             'test "`printf \'%s\' \"$iec\"     | jose jwk pub -i-`"'),
            ('test "`echo $ijwkset | jose jwk pub -i-`"',
             'test "`printf \'%s\' \"$ijwkset\" | jose jwk pub -i-`"'),
            ('test "`echo $iec     | jose jwk pub -i- -s`"',
             'test "`printf \'%s\' \"$iec\"     | jose jwk pub -i- -s`"'),
        ]
        applied.append("pub:%d" % self._replace_pairs(pub, pub_pairs))

        thp = os.path.join(tests_dir, "jose-jwk-thp")
        thp_pairs = [(
            '[ "`echo ${jwk} | jose jwk thp -i- -a S1`"',
            '[ "`printf \'%s\' \"${jwk}\" | jose jwk thp -i- -a S1`"')]
        applied.append("thp:%d" % self._replace_pairs(thp, thp_pairs))

        encr = os.path.join(tests_dir, "alg_encr.c")
        applied.append("alg_encr:%d" % self._replace_pairs(encr, [(
            "uint8_t *xxx = ebuf;", "uint8_t *xxx = ebuf;\n\t    (void)xxx;")]))

        self.output.info("JOSE_UPSTREAM_ADAPTATIONS=" + json.dumps(applied))

    def _replace_pairs(self, path, pairs):
        if not os.path.isfile(path):
            self.output.warning("missing file to adapt: %s" % path)
            return 0
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        hits = 0
        for old, new in pairs:
            if old in content:
                content = content.replace(old, new, 1)
                hits += 1
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return hits

    def _run_upstream_tests(self):
        """Run the upstream suite for real and gate the build on its summary.

        Registered at v14: 8 compiled programs (alg_hash, alg_sign, alg_encr,
        alg_wrap, alg_comp, api_b64, api_jws, api_jwe) + 16 `jose-*` shell
        scripts + tests/issue-75/issue75 = 25 tests. The numbers below come
        from meson's own summary, never from constants.
        """
        build_dir = self.build_folder
        log = os.path.join(build_dir, "meson-test.log")
        command = (
            'TMPDIR="{t}" TMP="{t}" TEMP="{t}" meson test -v -C "{b}" '
            '--num-processes 1 --no-rebuild --print-errorlogs > "{l}" 2>&1'
        ).format(t=build_dir, b=build_dir, l=log)
        self.run(command, env="conanbuild", ignore_errors=True)

        out = ""
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-40:]:
            self.output.info(line)

        def _count(pattern):
            match = re.search(pattern, out, flags=re.M)
            return int(match.group(1)) if match else 0

        ok = _count(r"^Ok:\s+(\d+)")
        failed = _count(r"^Fail:\s+(\d+)")
        skipped = _count(r"^Skipped:\s+(\d+)")
        timeout = _count(r"^Timeout:\s+(\d+)")
        not_run = _count(r"^Not run:\s+(\d+)")
        executed = ok + failed + skipped + timeout + not_run
        passed = executed > 0 and failed == 0 and skipped == 0 \
            and timeout == 0 and not_run == 0

        self.output.info("JOSE_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed" if passed else "failed",
            "framework": "meson",
            "command": command,
            "executed": executed,
            "passed": ok,
            "failed": failed,
            "skipped": skipped,
            "timeout": timeout,
        }, ensure_ascii=False))
        if not passed:
            raise RuntimeError(
                "upstream meson tests did not fully pass: executed=%d ok=%d "
                "fail=%d skipped=%d timeout=%d not_run=%d | %s" % (
                    executed, ok, failed, skipped, timeout, not_run,
                    self._failure_detail(out)))

    def _failure_detail(self, out):
        """Keep the real diff visible through the CI log truncation."""
        lines = [line for line in out.splitlines()
                 if "FAIL" in line or "Error" in line]
        return " ;; ".join(lines)[-700:]

    # ------------------------------------------------------------------ #
    # package
    # ------------------------------------------------------------------ #

    def package(self):
        Meson(self).install()

        # meson install can leave the narrow source umask (750) behind on
        # HMDFS, which the consumer cannot read from.
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.isfile(path):
                    try:
                        chmod(self, path, 0o755)
                    except OSError:
                        pass

        objcopy = _find_binutil("llvm-objcopy")
        signer = _find_binutil("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "binary-sign-tool/llvm-objcopy not found; packaged ELF files "
                "are left as installed")
        else:
            signed = 0
            total = 0
            for root, _, files in os.walk(self.package_folder):
                for name in files:
                    path = os.path.join(root, name)
                    if not os.path.isfile(path) or os.path.islink(path):
                        continue
                    with open(path, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                    total += 1
                    if _resign_elf(path, objcopy, signer):
                        signed += 1
            self.output.info("JOSE_REIGNED_ELF=%d/%d" % (signed, total))

        # Upstream installs its license under share/licenses/jose; publish a
        # conventional licenses/ copy as well.
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["jose"]
        # The package ships the `jose` CLI, hence the software-level
        # commands.json entry (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "jose")

        # Upstream's lib/meson.build uses shared_library() unconditionally, so
        # the packaged libjose.so.0.0.0 and bin/jose carry a DT_NEEDED on
        # libjansson.so but no RUNPATH that points at it (jansson ships only
        # an unversioned libjansson.so; openssl and zlib arrive as static
        # archives and are absorbed). Without the export, running the
        # installed CLI fails with "Error relocating ... json_*: symbol not
        # found". Declaring the requirement is also what makes the public
        # headers work: jose/jwk.h includes <jansson.h>.
        jansson = self.dependencies["jansson"]
        self.cpp_info.requires = ["jansson::jansson"]
        for libdir in (jansson.cpp_info.libdirs or ["lib"]):
            path = os.path.join(jansson.package_folder, libdir)
            if os.path.isdir(path):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", path)

        # Own lib directory, for consumers that link the shared libjose.
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

        # ...but conan 2.29 on a POSIX target does not put a dependency's
        # cpp_info.bindirs on PATH (measured in the consumer runenv: PATH only
        # carried the harmonybrew/hnp/system directories). Upstream ships the
        # `jose` CLI plus its man pages, so a consumer that just wants to run
        # the tool has to add the directory itself. Export it for both the run
        # and the build context.
        bindir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.prepend_path("PATH", bindir)
