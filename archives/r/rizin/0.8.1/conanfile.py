#!/usr/bin/env python3
"""Conan recipe — Rizin v0.8.1 (Meson build system).

Rizin is a fork of radare2, a reverse engineering framework with command-line
tooling (rizin, rz-asm, rz-bin, rz-diff, rz-find, rz-gg, rz-hash, rz-run,
rz-sign, rz-test). Adapted to OpenHarmony PC (aarch64).

Adaptation notes (see notes.md for full details):
  1. librz/util/thread.c: guard pthread_setcancelstate/type with
     HAVE_PTHREAD_SETCANCELSTATE feature probe (R8-compliant; see patch 0002/0003;
     HarmonyOS bionic libc does not implement POSIX thread cancel API).
  2. librz/debug/meson.build: extend linux/android branch with 'harmonyos' so
     linux_debug.c (defining linux_dbg_wait/reg_read/etc.) is compiled in.
     HarmonyOS native build reports host_machine.system()=='harmonyos'.
  3. OpenSSL include path injected via CPPFLAGS (rz_util.h includes
     <openssl/bn.h>, consumed by sibling librz/* targets).

Deps strategy ("only enable published" per W0/R36):
  use_sys_pcre2/libmagic/zlib/lz4/libzstd/openssl enabled (ohpcd published);
  use_sys_capstone/libzip/xxhash/libmspack/tree_sitter/softfloat/liblzma
  disabled (use Rizin vendored Meson subprojects).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
import os


class RizinConan(ConanFile):
    name = "rizin"
    version = "0.8.1"
    description = "Rizin is a fork of radare2, a reverse engineering framework with command-line tooling"
    license = "LGPL-3.0-only"
    homepage = "https://rizin.re"
    url = "https://github.com/rizinorg/rizin/releases/tag/v0.8.1"

    package_type = "application"
    build_system = "meson"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0/R36: only require ohpcd-published recipes.
        self.requires("pcre2/10.45")
        self.requires("file/5.48")        # provides libmagic.a / magic
        self.requires("zlib/1.3.1.1")     # PIC-enabled
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.7")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Meson wraps fetch GitHub subprojects (capstone-next, libdemangle, etc.) at configure
        # time; GitHub is unreachable from the OHOS build env. Pre-clone each git-form wrap
        # via the gitcode.com mirror into subprojects/<name>/ so meson's wrapdb finds them
        # already materialized and skips its own git fetch.
        import subprocess, shutil
        # R33: don't hardcode tool paths — read from env with sensible fallback so
        # the recipe survives a worker with a different HNP install location.
        HNP_BIN = os.environ.get("HNP_BIN_DIR", "/data/service/hnp/bin")
        GIT = os.path.join(HNP_BIN, "git")
        wrap_git_repos = {
            "blake3":              ("BLAKE3-team/BLAKE3", "2de3cb1a21d09cdee4c8b6b14513063198cf1b82"),
            "capstone-next":       ("capstone-engine/capstone", "895f2f2e10c245a45880c07c2666d498e62d8ecf"),
            "libdemangle":         ("rizinorg/rz-libdemangle", "d3083c18befed11069b65c57c2ad79fa5d9afba4"),
            "libmspack":           ("kyz/libmspack", "v1.11"),
            "rizin-grammar-c":     ("rizinorg/rizin-grammar-c", "815845762d59f727d79e7aa6f810688b2e1e35d2"),
            "sigdb":               ("rizinorg/sigdb", "main"),
            "softfloat":           ("rizinorg/softfloat", "537d18e71a51aea70f6b54334854f7014c6458c7"),
        }
        packagefiles = os.path.join(self.source_folder, "subprojects", "packagefiles")
        materialized = []
        for name, (repo, rev) in wrap_git_repos.items():
            dest = os.path.join(self.source_folder, "subprojects", name)
            clone_ok = os.path.isdir(os.path.join(dest, ".git"))
            # R41/#7: check git fetch/checkout returncodes — silent failure leaves the
            # subproject at the wrong rev and meson's wrapdb then treats a stale tree
            # as materialized. On failure mark clone_ok=False so the `if not clone_ok`
            # branch skips this subproject (meson reports it as not buildable, surfacing
            # the problem) instead of proceeding with a broken vendored tree.
            if clone_ok:
                rf = subprocess.run([GIT, "-C", dest, "fetch", "--depth", "1", "origin", rev],
                                    check=False, capture_output=True)
                rc = subprocess.run([GIT, "-C", dest, "checkout", rev],
                                    check=False, capture_output=True)
                if rf.returncode != 0 or rc.returncode != 0:
                    self.output.warning(f"git fetch/checkout failed for {name}@{rev} "
                                        f"(fetch={rf.returncode}, checkout={rc.returncode}): "
                                        f"{(rf.stderr or rc.stderr or b'').decode(errors='replace')[:200]}")
                    clone_ok = False
            else:
                # R39: vendored clone URL 用官方源 github.com;本地 CI 模拟可通过
                # GITHUB_MIRROR_PREFIX 环境变量注入镜像前缀(如 https://ghfast.top/)
                # 绕开 GitHub 不可达,CI 不设走官方源。
                _mirror = os.environ.get("GITHUB_MIRROR_PREFIX", "")
                r = subprocess.run(
                    [GIT, "clone", "--depth", "50",
                     f"{_mirror}https://github.com/{repo}.git", dest],
                    check=False, capture_output=True,
                )
                if r.returncode == 0 and os.path.isdir(os.path.join(dest, ".git")):
                    rf = subprocess.run(
                        [GIT, "-C", dest, "fetch", "--depth", "1",
                         f"{_mirror}https://github.com/{repo}.git", rev],
                        check=False, capture_output=True,
                    )
                    rc = subprocess.run([GIT, "-C", dest, "checkout", rev],
                                        check=False, capture_output=True)
                    if rf.returncode == 0 and rc.returncode == 0:
                        clone_ok = True
                    else:
                        self.output.warning(f"git fetch/checkout failed for {name}@{rev} after clone "
                                            f"(fetch={rf.returncode}, checkout={rc.returncode})")
            if not clone_ok:
                continue
            # meson's wrap-git mechanism copies packagefiles/<name>/* into the cloned source
            # root before treating the subproject as buildable. Pre-materialize those vendored
            # files (meson.build, etc.) so meson sees a complete subproject.
            pf_name = os.path.join(packagefiles, name)
            if os.path.isdir(pf_name):
                for entry in os.listdir(pf_name):
                    src = os.path.join(pf_name, entry)
                    dst = os.path.join(dest, entry)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src) and not os.path.exists(dst):
                        shutil.copytree(src, dst)
            materialized.append(name)
        # meson's wrap-git resolver runs git fetch against unreachable GitHub; we pre-fetched
        # the required rev into the cloned .git so meson's own fetch is a no-op. Re-point origin
        # to local repo as belt-and-suspenders.
        for name in materialized:
            dest = os.path.join(self.source_folder, "subprojects", name)
            subprocess.run([GIT, "-C", dest, "remote", "set-url", "origin", "."],
                           check=False, capture_output=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: non-system-name libs default dynamic; Conan manages dep chain.
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # NOTE: wrap_mode is a meson BUILT-IN option, not a project option — Conan's MesonToolchain
        # template writes [project options] from tc.project_options, but meson ignores wrap_mode
        # there. Inject it into [built-in options] in build() by patching the native.ini Conan
        # already wrote (Conan's Meson.configure() does NOT rewrite the ini, only reads it).
        # Only enable use_sys_* for published deps; vendored for the rest.
        tc.project_options["use_sys_pcre2"] = "enabled"
        tc.project_options["use_sys_magic"] = "enabled"
        tc.project_options["use_sys_zlib"] = "enabled"
        tc.project_options["use_sys_lz4"] = "enabled"
        tc.project_options["use_sys_libzstd"] = "enabled"
        tc.project_options["use_sys_openssl"] = "enabled"
        tc.project_options["use_sys_capstone"] = "disabled"
        tc.project_options["use_sys_libzip"] = "disabled"
        tc.project_options["use_sys_lzma"] = "disabled"
        tc.project_options["use_sys_xxhash"] = "disabled"
        tc.project_options["use_sys_libmspack"] = "disabled"
        tc.project_options["use_sys_tree_sitter"] = "disabled"
        tc.project_options["use_sys_softfloat"] = "disabled"
        tc.generate()
        # OHOS conan lacks MesonDeps; use PkgConfigDeps so meson's dependency('libpcre2-8')
        # etc. resolve via pkg-config. PkgConfigDeps writes .pc into generators_folder.
        PkgConfigDeps(self).generate()
        # meson.build looks up deps by names Conan doesn't emit: create alias .pc files.
        import re
        pc_dir = self.generators_folder
        if pc_dir and os.path.isdir(pc_dir):
            aliases = {
                "libpcre2-8": "pcre2",    # meson: dependency('libpcre2-8')
                "libmagic":   "file",     # meson: dependency('libmagic')
                "liblz4":     "lz4",      # meson: dependency('liblz4')
            }
            for alias, real in aliases.items():
                real_pc = os.path.join(pc_dir, real + ".pc")
                alias_pc = os.path.join(pc_dir, alias + ".pc")
                if os.path.isfile(real_pc) and not os.path.isfile(alias_pc):
                    with open(real_pc) as fr:
                        body = fr.read()
                    body = re.sub(r"^Name:.*$", "Name: " + alias, body, count=1, flags=re.MULTILINE)
                    with open(alias_pc, "w") as fw:
                        fw.write(body)
        # NOTE: absolute tool paths (ar/ranlib/strip/ld) are injected in build()
        # via Conan's extra_machine_files conf — NOT here. The old INI-rewrite
        # below was retired (build() lands the patch after tc.generate()).
        # Conan's Meson() spawns meson as a subprocess; inject env via meson's own
        # [built-in options] (c_args, cpp_args, pkg_config_path) which Conan's MesonToolchain
        # already serializes into conan_meson_native.ini. Avoid register_env_script (OHOS conan bug).
        # Locate OpenSSL package_folder via self.dependencies (Conan 2.x standard API) so we
        # can inject -I<inc> into [built-in options] c_args/cpp_args in build() — Conan's template
        # leaves c_args empty and pkg-config for openssl doesn't expose bn.h's parent dir.
        openssl_inc = None
        # self.dependencies is a ConanFileDependencies object (NOT a dict) — iterate .values()
        deps = getattr(self, "dependencies", None)
        dep_items = list(deps.values()) if deps else []
        for dep in dep_items:
            if dep.ref.name == "openssl":
                pf = dep.package_folder
                openssl_inc = os.path.join(pf, "include") if pf else None
        self._openssl_inc = openssl_inc  # stash for build() INI patching

    def build(self):
        apply_conandata_patches(self)
        # Inject wrap_mode into native.ini [built-in options] section.
        # wrap_mode is a meson built-in (not project) option; Conan's MesonToolchain template
        # only hardcodes buildtype/backend/cpp_std etc. in [built-in options], with no slot for
        # arbitrary keys. Patch the INI Conan already wrote (during generate()) NOW, before
        # meson.configure() reads it. Conan's Meson.configure() does NOT rewrite the INI.
        # Use 'default' (NOT nodownload/forcefallback): nodownload disables fallback subproject
        # lookup breaking dependency('rzgdb'); forcefallback forces download attempts. With
        # 'default', meson's _resolve() sees vendored subprojects have meson.build → returns
        # early (line 565 has_buildfile()), NO download attempted. dependency('rzgdb') without
        # pkg-config auto-falls back to vendored rzgdb subproject (has meson.build).
        native_ini = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self.output.warning(f"PATCH wrap_mode native_ini={native_ini} exists={os.path.isfile(native_ini)} gen={self.generators_folder}")
        if os.path.isfile(native_ini):
            with open(native_ini) as f:
                content = f.read()
            self.output.warning(f"PATCH before wrap_mode lines = {[l for l in content.splitlines() if 'wrap_mode' in l]}")
            # 1. Conan's MesonToolchain defaults wrap_mode to 'nofallback' and writes it into
            #    [project options] — meson honors that and disables fallback subproject lookup,
            #    breaking dependency('rzgdb') calls relying on vendored subprojects. Remove any
            #    wrap_mode line from [project options] (it's a built-in, doesn't belong there).
            import re
            content = re.sub(r"^wrap_mode\s*=.*\n", "", content, flags=re.MULTILINE)
            # 2. Inject wrap_mode = 'default' into [built-in options] (correct section for meson
            #    built-ins). 'default' lets meson auto-fallback to vendored subprojects (which
            #    have meson.build → _resolve() has_buildfile() returns early, no download).
            marker = "[built-in options]\n"
            inject = "wrap_mode = 'default'\n"
            if "wrap_mode = 'default'" not in content:
                if marker in content:
                    content = content.replace(marker, marker + inject, 1)
                else:
                    content = marker + inject + "\n" + content
            # 3. Inject -I<openssl_inc> into [built-in options] c_args/cpp_args so ninja
            #    compiles find openssl/bn.h. Conan's MesonToolchain template hardcodes
            #    c_args = [] (empty) in [built-in options]; meson uses built-in c_args for
            #    global C compiler flags. Replace the empty c_args/cpp_args lines with paths.
            #    Note: patch 0002's pthread_setcancelstate guard uses meson-probed
            #    HAVE_PTHREAD_SETCANCELSTATE (patch 0003), not -DPTHREAD_CANCEL_DISABLE —
            #    no -D macro injection needed here.
            oi = self._openssl_inc
            if oi and os.path.isdir(oi):
                iarg = "['-I" + oi + "']"
                self.output.warning(f"PATCH openssl_inc={oi} c_args before={re.findall(r'^c_args.*', content, flags=re.MULTILINE)}")
                content = re.sub(r"^(c_args\s*=).*?(\s*\+ preprocessor_definitions)?$", r"\1 " + iarg + r"\2", content, count=1, flags=re.MULTILINE)
                content = re.sub(r"^(cpp_args\s*=).*?(\s*\+ preprocessor_definitions)?$", r"\1 " + iarg + r"\2", content, count=1, flags=re.MULTILINE)
                self.output.warning(f"PATCH c_args after={re.findall(r'^c_args.*', content, flags=re.MULTILINE)}")
            with open(native_ini, "w") as f:
                f.write(content)
        # Conan's MesonToolchain.generate() wrote conan_meson_native.ini during generate(),
        # but it OMITS ar/ranlib/strip/ld from [binaries] — meson then PATH-looks-up 'llvm-ar'
        # which fails (/data/service/hnp/bin not in meson subprocess PATH). Conan overwrites
        # the INI on Meson.configure(), so patching the file is futile. Instead, register an
        # EXTRA machine file via Conan's own conf mechanism (tools.meson.mesontoolchain:
        # extra_machine_files) — Meson.configure() will append it via --native-file, atomically.
        # Conan's Meson.configure() passes extra_machine_files paths VERBATIM to meson's
        # --native-file arg. self.generators_folder during build() is already "<gen>/conan"
        # (Conan scopes the MesonToolchain outputs under conan/), so an absolute path built
        # from self.generators_folder lands where meson's --native-file looks. Register and
        # write to the SAME absolute path so meson finds the file.
        extra_ini_path = os.path.join(self.generators_folder, "ohos_extra_binaries.ini")
        # R33: read HNP tool dir from env with sensible fallback (survives a worker
        # whose HNP install differs from /data/service/hnp/bin).
        hnp_bin = os.environ.get("HNP_BIN_DIR", "/data/service/hnp/bin")
        extra_ini_content = (
            "[binaries]\n"
            "ar = '" + hnp_bin + "/llvm-ar'\n"
            "ranlib = '" + hnp_bin + "/llvm-ranlib'\n"
            "strip = '" + hnp_bin + "/llvm-strip'\n"
            "ld = '" + hnp_bin + "/ld.lld'\n"
        )
        os.makedirs(os.path.dirname(extra_ini_path), exist_ok=True)
        with open(extra_ini_path, "w") as f:
            f.write(extra_ini_content)
        conf_key = "tools.meson.mesontoolchain:extra_machine_files"
        existing = self.conf.get(conf_key, default=[], check_type=list)
        if extra_ini_path not in existing:
            existing.append(extra_ini_path)
        self.conf.define(conf_key, existing)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "rz_core", "rz_main", "rz_config", "rz_cons", "rz_util",
            "rz_io", "rz_socket", "rz_bin", "rz_lang", "rz_asm", "rz_analysis",
            "rz_arch", "rz_bp", "rz_crypto", "rz_debug", "rz_egg", "rz_flag",
            "rz_hash", "rz_magic", "rz_reg", "rz_sign", "rz_syscall", "rz_type",
        ]
        self.cpp_info.includedirs = ["include/librz"]  # rz_core.h etc. live under p/include/librz/
        self.cpp_info.bindirs = ["bin"]
        # Command-line tools (R38 declared in archives/r/rizin/commands.json)
        self.cpp_info.exes = [
            "rizin", "rz-asm", "rz-ax", "rz-bin", "rz-diff", "rz-find",
            "rz-gg", "rz-hash", "rz-run", "rz-sign", "rz-test",
        ]
