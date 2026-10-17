#!/usr/bin/env python3
"""Conan recipe -- libmesode 0.10.1 (direct compiler build, no autotools).

Why no autotools (preflight evidence, 2026-09-16):
- Upstream ships no configure (GitHub archive); bootstrap needs autoreconf.
- Preflight sandbox has no native autoreconf
  ("/bin/sh: autoreconf: inaccessible or not found") and conan-provided
  autoconf cannot be built there: m4/1.4.19 source build fails at
  configure[139] because the profile re-execs configure with
  /data/service/hnp/bin/bash, which is inaccessible in the sandbox.
  So autoreconf is unobtainable in this environment; pulling autoconf as a
  tool_requires only moves the failure into the m4 dependency build.
- Upstream build is faithfully reproducible without autotools:
  configure.ac defines NO config.h (no AC_CONFIG_HEADERS), so the feature
  probes never materialize as compiler defines; Makefile.am is
  non-recursive with an explicit source list and explicit per-test source
  mappings. This recipe compiles the exact upstream source list with the
  toolchain compiler and drives the exact upstream test programs using the
  automake exit-code protocol (exit 0 == PASS, same as `make check`).
"""

import json as _json
import os as _os
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.files import apply_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

UPSTREAM_TEST_COUNT = 12
UPSTREAM_TEST_NAMES = [
    "tests/check_parser",
    "tests/test_sha1",
    "tests/test_md5",
    "tests/test_rand",
    "tests/test_scram",
    "tests/test_ctx",
    "tests/test_base64",
    "tests/test_hash",
    "tests/test_jid",
    "tests/test_snprintf",
    "tests/test_string",
    "tests/test_resolver",
]

# Exact upstream library source list (Makefile.am libmesode_la_SOURCES,
# TLS enabled branch + expat parser, examples excluded: noinst_PROGRAMS,
# neither installed nor part of `make check`).
LIB_SOURCES = [
    "src/auth.c",
    "src/conn.c",
    "src/crypto.c",
    "src/ctx.c",
    "src/event.c",
    "src/handler.c",
    "src/hash.c",
    "src/jid.c",
    "src/md5.c",
    "src/rand.c",
    "src/resolver.c",
    "src/sasl.c",
    "src/scram.c",
    "src/sha1.c",
    "src/snprintf.c",
    "src/sock.c",
    "src/stanza.c",
    "src/util.c",
    "src/uuid.c",
    "src/tls_openssl.c",
    "src/parser_expat.c",
]

# libmesode internal TLS symbols (tls.h) collide with OpenSSL 3.x
# libssl.a internal symbols (ssl/tls_common.c defines global tls_free;
# preflight 2026-09-16: ld.lld duplicate symbol tls_free when linking
# libmesode.so against static openssl/3.5.6.1.1). Public API is xmpp_* only
# (version-script already hides the rest), so rename all tls_* at compile
# time to mesode_tls_* via -D. Applied to every lib object AND every test
# compile so declarations and calls stay consistent.
TLS_RENAMES = [
    "tls_initialize",
    "tls_shutdown",
    "tls_new",
    "tls_free",
    "tls_peer_cert",
    "tls_set_credentials",
    "tls_start",
    "tls_stop",
    "tls_error",
    "tls_pending",
    "tls_read",
    "tls_write",
    "tls_clear_pending_write",
    "tls_is_recoverable",
]
# Exact upstream test mappings (Makefile.am check_PROGRAMS entries).
# use_lib=True links the static lib (mirrors upstream `-static` LDFLAGS,
# giving tests access to internal symbols just like `make check`).
UPSTREAM_TESTS = [
    ("check_parser", ["tests/check_parser.c"], True),
    ("test_sha1", ["tests/test_sha1.c", "src/sha1.c"], False),
    ("test_md5", ["tests/test_md5.c", "tests/test.c", "src/md5.c"], False),
    ("test_rand", ["tests/test_rand.c", "tests/test.c", "src/sha1.c"], False),
    ("test_scram", ["tests/test_scram.c", "tests/test.c", "src/sha1.c"], False),
    ("test_ctx", ["tests/test_ctx.c"], True),
    ("test_base64", ["tests/test_base64.c", "tests/test.c"], True),
    ("test_hash", ["tests/test_hash.c"], True),
    ("test_jid", ["tests/test_jid.c"], True),
    ("test_snprintf", ["tests/test_snprintf.c"], False),
    ("test_string", ["tests/test_string.c"], True),
    ("test_resolver", ["tests/test_resolver.c"], True),
]


def _is_usable_tool(path):
    # Absolute path: accept only after existence check; bare name: PATH lookup.
    # NOTE: do not gate on os.access(X_OK) alone (HMDFS ignores chmod); rely
    # on isfile for absolute paths and shutil.which for PATH lookup, then let
    # the actual invocation prove executability.
    if not path:
        return False
    path = path.strip().strip('"').strip("'")
    if not path:
        return False
    if _os.path.isabs(path):
        return _os.path.isfile(path)
    return _shutil.which(path) is not None


def _resolve_tool(conanfile, configured, env_keys, fallbacks, use_conf=False):
    # Order: configured absolute value (validated) -> tool-specific env
    # vars -> build-system compiler config (CC only) -> PATH lookup for
    # generic names. Never mix build tools (make/cmake) into compiler
    # candidates: preflight 2026-09-16 picked HMBS_MAKE
    # (/storage/.../usr/local/bin/make) as CC and then failed with
    # `make $CFLAGS -c resolv_probe.c` (rc=2, make usage output).
    # Returns a quoted executable string usable in shell commands.
    candidates = []
    if configured:
        candidates.append(configured)
    for _env in env_keys:
        _v = _os.environ.get(_env)
        if _v and _v not in candidates:
            candidates.append(_v)
    if use_conf:
        try:
            _conf_cc = conanfile.conf.get("tools.build:compiler_executables")
            if isinstance(_conf_cc, dict):
                for _k in ("c", "cpp"):
                    _v = _conf_cc.get(_k)
                    if _v and _v not in candidates:
                        candidates.append(_v)
        except Exception:
            pass
    candidates.extend(fallbacks)
    for _c in candidates:
        if _is_usable_tool(_c):
            if _os.path.isabs(_c.strip().strip('"').strip("'")):
                return '"%s"' % _c.strip().strip('"').strip("'")
            found = _shutil.which(_c.strip().strip('"').strip("'"))
            if found:
                return '"%s"' % found
            return _c
    return None


class LibmesodeConan(ConanFile):
    name = "libmesode"
    version = "0.10.1"
    description = "Lightweight XMPP library, fork of libstrophe for Profanity XMPP client"
    license = "MIT"
    homepage = "https://github.com/profanity-im/libmesode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libmesode is supported only on Linux/OHOS, got: %s" % self.settings.os)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require arch=armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("expat/2.8.2.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # AutotoolsToolchain is used ONLY as a carrier for the cross
        # toolchain environment (CC/CFLAGS/LDFLAGS/AR with sysroot etc. in
        # conanbuild). No configure/make is ever invoked.
        tmpdir = _os.path.join(self.build_folder, "tmp")
        _os.makedirs(tmpdir, exist_ok=True)
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)

    def _dep_flags(self):
        inc, libd, libs, defs = [], [], [], []
        for _ref, _dep in self.dependencies.items():
            cpp = _dep.cpp_info
            for _d in (cpp.includedirs or []):
                if _os.path.isabs(_d):
                    inc.append("-I" + _d)
            for _d in (cpp.libdirs or []):
                if _os.path.isabs(_d):
                    libd.append("-L" + _d)
            for _lib in (cpp.libs or []):
                libs.append("-l" + _lib)
            for _lib in (cpp.system_libs or []):
                libs.append("-l" + _lib)
            for _dd in (cpp.defines or []):
                defs.append("-D" + _dd)
        return inc, libd, libs, defs

    def _emit_upstream(self, data):
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + _json.dumps(data, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(_os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as _f:
                _json.dump(data, _f)
        except OSError as exc:
            self.output.warning("persist hmbs_upstream.json failed: %s" % exc)

    def _sh_log(self, cmd, logname):
        # Run a shell command under conanbuild, capturing output to a file.
        # Never swallows diagnostics: failures print the log tail.
        log = _os.path.join(self.build_folder, logname)
        rc = self.run('%s >"%s" 2>&1' % (cmd, log),
                      cwd=self.build_folder, env="conanbuild",
                      ignore_errors=True)
        try:
            with open(log, encoding="utf-8", errors="replace") as _f:
                lines = _f.read().splitlines()
        except OSError:
            lines = ["<unreadable log>"]
        tail = lines[-25:] if len(lines) > 25 else lines
        if rc != 0:
            self.output.info("command failed (rc=%s): %s" % (rc, cmd))
            for _line in tail:
                self.output.info("  | " + _line)
        return rc

    def _probe_resolver(self, inc, libd, cc):
        # Upstream configure.ac hard-errors when res_query() is not found.
        # This sandbox instead needs diagnostics + graceful degradation, so
        # probe headers and symbol separately and return capabilities:
        #   (have_resolv_h, have_res_query, resolv_libs)
        # resolver_srv_lookup_buf() (the only thing upstream tests exercise)
        # is pure packet parsing and never needs res_query.
        # cc is the validated compiler (absolute PATH fallback applied);
        # never use bare $CC (preflight: profile CC may be inaccessible).
        inc_s = " ".join(inc)
        libd_s = " ".join(libd)
        pj = _os.path.join(self.build_folder, "resolv_probe.c")

        def _write(body):
            with open(pj, "w", encoding="utf-8", newline="\n") as _f:
                _f.write(body)

        def _compile_ok(extra=""):
            return self._sh_log(
                '%s $CFLAGS %s %s -c "%s" -o "%s"'
                % (cc, inc_s, extra, pj, pj + ".o"), "probe_compile.log") == 0

        def _link_ok(extra_libs):
            return self._sh_log(
                '%s $CFLAGS "%s" -o "%s" $LDFLAGS %s %s'
                % (cc, pj + ".o", pj + ".bin", libd_s, extra_libs),
                "probe_link.log") == 0

        hdrs = ("#include <sys/types.h>\n"
                "#include <netinet/in.h>\n"
                "#include <arpa/nameser.h>\n"
                "#include <resolv.h>\n"
                "#include <netdb.h>\n")
        call = ("int main(void) {\n"
                "    unsigned char a[64];\n"
                "    int r = res_query(\"x\", 1, 33, a, sizeof(a));\n"
                "    return r != 0 ? 0 : 0;\n"
                "}\n")
        nodecl = ("extern int res_query(const char *dname, int class_, "
                  "int type, unsigned char *answer, int anslen);\n"
                  "int main(void) {\n"
                  "    unsigned char a[64];\n"
                  "    int r = res_query(\"x\", 1, 33, a, sizeof(a));\n"
                  "    return r != 0 ? 0 : 0;\n"
                  "}\n")

        _write(hdrs + "int main(void) { return 0; }\n")
        have_h = _compile_ok()
        self.output.info("probe: resolver headers present: %s" % have_h)

        have_q, qlibs = False, []
        if have_h:
            _write(hdrs + call)
            if _compile_ok():
                for libs_try in ("-lresolv", ""):
                    if _link_ok(libs_try):
                        have_q, qlibs = True, libs_try.split()
                        break
        if not have_q:
            # Headers missing (or unusable): retry with a manual declaration
            # to distinguish "no headers" from "no symbol".
            _write(nodecl)
            if _compile_ok():
                for libs_try in ("-lresolv", ""):
                    if _link_ok(libs_try):
                        have_q, qlibs = True, libs_try.split()
                        break
        self.output.info("probe: res_query usable: %s LIBS='%s'"
                         % (have_q, " ".join(qlibs)))
        return have_h, have_q, qlibs

    def _adapt_resolver_c(self, have_h, have_q):
        # OHOS adaptation of src/resolver.c (feature macros, no platform
        # macros): declare res_query manually when bind headers are absent,
        # and degrade resolver_srv_lookup() to NOT_FOUND when the symbol is
        # absent. xmpp_connect_client() is documented to fall back to
        # domain:default_port on NOT_FOUND, and the tested
        # resolver_srv_lookup_buf() parser is untouched.
        path = _os.path.join(self.source_folder, "src", "resolver.c")
        with open(path, encoding="utf-8") as _f:
            text = _f.read()
        if "OHOS adaptation: no res_query()" in text:
            self.output.info("src/resolver.c already adapted; skipping")
            return
        old_inc = ("#include <netinet/in.h>\n"
                   "#include <arpa/nameser.h>\n"
                   "#include <resolv.h>             /* res_query */\n")
        new_inc = ("#include <netinet/in.h>\n"
                   "#ifdef HAVE_RESOLV_H\n"
                   "#include <arpa/nameser.h>\n"
                   "#include <resolv.h>             /* res_query */\n"
                   "#else\n"
                   "/* OHOS adaptation: libc without bind resolver headers;\n"
                   " * the symbol itself is build-time probed (HAVE_RES_QUERY)\n"
                   " * and declared here. */\n"
                   "extern int res_query(const char *dname, int class_, "
                   "int type,\n"
                   "                     unsigned char *answer, int anslen);\n"
                   "#endif\n")
        if text.count(old_inc) != 1:
            raise ConanException(
                "src/resolver.c include block not found exactly once; "
                "upstream layout changed, refusing silent adaptation")
        text = text.replace(old_inc, new_inc)
        old_call = ("    *srv_rr_list = NULL;\n"
                    "\n"
                    "    len = res_query(fulldomain, MESSAGE_C_IN, "
                    "MESSAGE_T_SRV, buf, sizeof(buf));\n"
                    "\n"
                    "    if (len > 0)\n"
                    "        set = resolver_srv_lookup_buf(ctx, buf, "
                    "(size_t)len, srv_rr_list);\n")
        new_call = ("    *srv_rr_list = NULL;\n"
                    "\n"
                    "#ifdef HAVE_RES_QUERY\n"
                    "    len = res_query(fulldomain, MESSAGE_C_IN, "
                    "MESSAGE_T_SRV, buf, sizeof(buf));\n"
                    "\n"
                    "    if (len > 0)\n"
                    "        set = resolver_srv_lookup_buf(ctx, buf, "
                    "(size_t)len, srv_rr_list);\n"
                    "#else\n"
                    "    /* OHOS adaptation: no res_query() on this platform;\n"
                    "     * report NOT_FOUND so xmpp_connect_client() falls\n"
                    "     * back to domain:default_port as documented. */\n"
                    "    (void)fulldomain;\n"
                    "    (void)buf;\n"
                    "    (void)len;\n"
                    "#endif\n")
        if text.count(old_call) != 1:
            raise ConanException(
                "resolver_srv_lookup body not found exactly once; "
                "upstream layout changed, refusing silent adaptation")
        text = text.replace(old_call, new_call)
        with open(path, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(text)
        self.output.info("src/resolver.c adapted (HAVE_RESOLV_H=%s "
                         "HAVE_RES_QUERY=%s)" % (have_h, have_q))

    def build(self):
        apply_conandata_patches(self)
        tmpdir = _os.path.join(self.build_folder, "tmp")
        _os.makedirs(tmpdir, exist_ok=True)
        _os.environ["TMPDIR"] = tmpdir
        _os.environ["TMP"] = tmpdir
        _os.environ["TEMP"] = tmpdir

        # Resolve toolchain executables with validation + PATH fallback.
        # Preflight evidence (2026-09-16): profile CC pointed at
        # /data/service/hnp/bin/clang ("inaccessible or not found", rc=127)
        # and conanbuild env had no AR at all. A configured absolute path is
        # accepted only after existence check, otherwise fall back to generic
        # names via PATH (conanbuild PATH already has HMBS tool dirs first).
        cc = _resolve_tool(self, _os.environ.get("CC"),
                           ("HMBS_CC", "CC"),
                           ["cc", "clang", "gcc", "aarch64-linux-gnu-gcc"],
                           use_conf=True)
        if cc is None:
            raise ConanException(
                "no usable C compiler: configured CC=%r not found and "
                "PATH lookup for cc/clang/gcc failed" % _os.environ.get("CC"))
        ar = _resolve_tool(self, _os.environ.get("AR"),
                           ("HMBS_AR", "AR"),
                           ["ar", "llvm-ar", "aarch64-linux-gnu-ar"])
        if ar is None:
            raise ConanException(
                "no usable archiver: configured AR=%r not found and "
                "PATH lookup for ar/llvm-ar failed" % _os.environ.get("AR"))
        self.output.info("resolved CC=%s AR=%s" % (cc, ar))

        inc, libd, libs, defs = self._dep_flags()
        have_h, have_q, resolv = self._probe_resolver(inc, libd, cc)
        self._adapt_resolver_c(have_h, have_q)
        feat = []
        if have_h:
            feat.append("-DHAVE_RESOLV_H")
        if have_q:
            feat.append("-DHAVE_RES_QUERY")
        inc_s = " ".join(["-I" + self.source_folder,
                          "-I" + _os.path.join(self.source_folder, "src"),
                          "-I" + _os.path.join(self.source_folder, "tests")]
                         + inc + defs + feat
                         + ["-D%s=mesode_%s" % (s, s) for s in TLS_RENAMES])
        libd_s = " ".join(libd)
        libs_s = " ".join(libs)
        resolv_s = " ".join(resolv)
        self.output.info("tls renames: %s" % " ".join(TLS_RENAMES))

        objdir = _os.path.join(self.build_folder, "objs")
        bindir = _os.path.join(self.build_folder, "uptest")
        _os.makedirs(objdir, exist_ok=True)
        _os.makedirs(bindir, exist_ok=True)

        for src in LIB_SOURCES:
            obj = _os.path.join(objdir, src.replace("/", "_") + ".o")
            self.run(
                '%s $CFLAGS -fPIC -Wall %s -c "%s" -o "%s"'
                % (cc, inc_s, _os.path.join(self.source_folder, src), obj),
                cwd=self.source_folder, env="conanbuild")

        static_lib = _os.path.join(objdir, "libmesode.a")
        self.run('%s rcs "%s" "%s"/*.o' % (ar, static_lib, objdir),
                 cwd=self.source_folder, env="conanbuild")

        if self.options.shared:
            # Upstream hides non-public symbols
            # (-export-symbols-regex '^xmpp_'); reproduce with a version
            # script, falling back to a plain link (logged) if the
            # platform linker rejects it.
            mapfile = _os.path.join(objdir, "mesode.map")
            with open(mapfile, "w", encoding="utf-8", newline="\n") as _f:
                _f.write("{ global: xmpp_*; local: *; };\n")
            shared_lib = _os.path.join(objdir, "libmesode.so")
            rc = self.run(
                '%s $CFLAGS -shared -o "%s" "%s"/*.o $LDFLAGS %s %s %s '
                '-Wl,--version-script,"%s" -Wl,-soname,libmesode.so'
                % (cc, shared_lib, objdir, libd_s, libs_s, resolv_s, mapfile),
                cwd=self.source_folder, env="conanbuild", ignore_errors=True)
            if rc != 0:
                self.output.warning(
                    "version-script link failed (rc=%s); retrying plain link" % rc)
                self.run(
                    '%s $CFLAGS -shared -o "%s" "%s"/*.o $LDFLAGS %s %s %s '
                    "-Wl,-soname,libmesode.so"
                    % (cc, shared_lib, objdir, libd_s, libs_s, resolv_s),
                    cwd=self.source_folder, env="conanbuild")

        self._run_upstream_tests(cc, inc_s, libd_s, libs_s, resolv_s,
                                 static_lib, bindir)

    def _run_upstream_tests(self, cc, inc_s, libd_s, libs_s, resolv_s,
                            static_lib, bindir):
        rpath = ":".join(
            _d for _ref, _dep in self.dependencies.items()
            for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d))
        passed, failed = 0, 0
        for name, sources, use_lib in UPSTREAM_TESTS:
            srcs = " ".join('"%s"' % _os.path.join(self.source_folder, s)
                            for s in sources)
            binpath = _os.path.join(bindir, name)
            if use_lib:
                # static lib on the link line (mirrors upstream `-static`),
                # dep libs after objects for left-to-right resolution.
                cmd = ('%s $CFLAGS -Wall %s %s -o "%s" "%s" $LDFLAGS %s '
                       '%s %s'
                       % (cc, inc_s, srcs, binpath, static_lib, libd_s,
                          libs_s, resolv_s))
            else:
                cmd = ('%s $CFLAGS -Wall %s %s -o "%s"'
                       % (cc, inc_s, srcs, binpath))
            self.run(cmd, cwd=self.source_folder, env="conanbuild")
            if not _os.path.isfile(binpath):
                raise ConanException("upstream test binary missing: %s" % binpath)
            if _os.path.getsize(binpath) == 0:
                raise ConanException("upstream test binary empty: %s" % binpath)
            self.output.info("RUN upstream test: %s" % name)
            rc = self.run(
                'LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
                '"%s"' % (rpath + ":" if rpath else "", binpath),
                cwd=self.source_folder, env="conanbuild", ignore_errors=True)
            if rc == 0:
                passed += 1
            else:
                failed += 1
                self.output.error("upstream test FAILED: %s (rc=%s)" % (name, rc))
        data = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake-check",
            "command": "direct cc driver: 12 TESTS programs per Makefile.am "
                       "check_PROGRAMS mapping, automake exit-code protocol",
            "discovered": UPSTREAM_TEST_COUNT,
            "executed": UPSTREAM_TEST_COUNT,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self._emit_upstream(data)
        if failed:
            raise ConanException(
                "upstream tests failed: %d/%d" % (failed, UPSTREAM_TEST_COUNT))

    def package(self):
        incdir = _os.path.join(self.package_folder, "include")
        libdir = _os.path.join(self.package_folder, "lib")
        _os.makedirs(incdir, exist_ok=True)
        _os.makedirs(libdir, exist_ok=True)
        copy(self, "mesode.h", src=self.source_folder, dst=incdir,
             keep_path=False)
        objdir = _os.path.join(self.build_folder, "objs")
        if self.options.shared:
            copy(self, "libmesode.so", src=objdir, dst=libdir, keep_path=False)
        else:
            copy(self, "libmesode.a", src=objdir, dst=libdir, keep_path=False)
        # pkg-config file from upstream libmesode.pc.in substitutions.
        _, libd, libs, _ = self._dep_flags()
        pc_dir = _os.path.join(libdir, "pkgconfig")
        _os.makedirs(pc_dir, exist_ok=True)
        pc_req = "expat openssl"
        pc_priv = " ".join(libs)
        with open(_os.path.join(pc_dir, "libmesode.pc"),
                  "w", encoding="utf-8", newline="\n") as _f:
            _f.write(
                "prefix=%s\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: libmesode\n"
                "Description: A simple, lightweight C library for writing "
                "XMPP clients\n"
                "URL: https://github.com/profanity-im/libmesode\n"
                "Version: 0.10.1\n"
                "Requires:\n"
                "Requires.private: %s\n"
                "Libs: -L${libdir} -lmesode\n"
                "Libs.private: %s\n"
                "Cflags: -I${includedir}\n"
                % (self.package_folder.replace("\\", "/"), pc_req, pc_priv))
        for lic in ("LICENSE.txt", "MIT-LICENSE.txt", "GPL-LICENSE.txt"):
            try:
                copy(self, lic, src=self.source_folder,
                     dst=_os.path.join(self.package_folder, "licenses"),
                     keep_path=False)
            except Exception as exc:
                self.output.warning("license copy %s failed: %s" % (lic, exc))
        try:
            _src = _os.path.join(self.build_folder, "hmbs_upstream.json")
            if _os.path.isfile(_src):
                _dst_dir = _os.path.join(self.package_folder, "res")
                _os.makedirs(_dst_dir, exist_ok=True)
                copy(self, "hmbs_upstream.json", src=self.build_folder,
                     dst=_dst_dir, keep_path=False)
            else:
                self.output.warning(
                    "hmbs_upstream.json not found in build folder; "
                    "package will lack upstream evidence")
        except Exception as exc:
            self.output.warning("shipping hmbs_upstream.json failed: %s" % exc)

    def package_info(self):
        self.cpp_info.libs = ["mesode"]
        self.cpp_info.set_property("cmake_file_name", "libmesode")
        self.cpp_info.set_property("cmake_target_name", "libmesode::libmesode")
        self.cpp_info.set_property("pkg_config_name", "libmesode")
