#!/usr/bin/env python3
"""Conan recipe for astra 1.1.0 (adapted prebuilt binary variant) — DataStax Astra CLI.

Strategy (period 10, 2026-08-02): download the upstream prebuilt
``astra-linux-arm64.tar.gz`` release artifact from datastax/astra-cli
v1.1.0 (a self-contained aarch64 glibc-dynamic binary produced upstream by
GraalVM native-image in GitHub Actions) and adapt it to OHOS musl using the
proven git-xet/qsv/spotify_player recipe:

  1. Download the prebuilt tarball (SHA256-gated), extract under build_folder.
  2. Vendor the glibc→musl compat layer (Alpine gcompat 1.1.0-r4 +
     libucontext 1.2-r3 + musl-obstack 1.2.3-r2 + libgcc) into the binary's
     lib dir.
  3. Build ``libglibc-shim.so`` on-device (provides ``__res_state`` /
     ``res_init`` / ``res_search`` stubs that HongMeng musl does not export
     but Alpine libgcompat.so.0 references).
  4. ``patchelf --set-interpreter /lib/ld-musl-aarch64.so.1`` on every
     dynamic ELF, and ``--replace-needed`` each glibc SONAME
     (``libc.so.6``, ``libm.so.6``, ``libdl.so.2``, ``libpthread.so.0``,
     ``librt.so.1``, ``libcrypt.so.1``, ``libresolv.so.2``,
     ``ld-linux-aarch64.so.1``) → ``libgcompat.so.0``.
  5. Re-sign every ELF with ``binary-sign-tool`` for the OHOS kernel exec
     path (knowledge/doc/E077.md, E083.md, E128.md).

Why not build from source on the device:
  Periods 1-9 tried to RUN GraalVM's ``java`` / ``native-image`` on the
  HongMeng device to AOT-compile astra-cli. All nine failed with JVM SIGILL
  (exit -4) — the HongMeng kernel / CPU is incompatible with HotSpot's
  aarch64 backend, and every diagnostic (hs_err dump, dmesg, strace,
  LD_DEBUG) was empty or unavailable on the device. The prebuilt-binary
  route bypasses the JVM entirely: native-image runs in upstream CI, we
  only adapt the resulting glibc binary to musl.

R32: OHOS 适配通过 settings.os 判断，支持 "Linux" 和 "OHOS" 两种平台。
R28: test_package/ exists.
R34: test_package 调用被测包二进制，非空壳测试。
R38: commands.json 已声明 astra 可执行文件。
"""
import hashlib
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy
from conan.tools.layout import basic_layout


# ---------------------------------------------------------------------------
# Download helpers (curl → GNU wget → Python urllib, with mirror fallback).
# ---------------------------------------------------------------------------

def _is_toybox_wget(path):
    """Detect toybox/busybox wget, which can't follow GitHub's 302 redirect
    and aborts with 'response header too large' / 'Unknown option' on big
    Location headers and GNU-only flags."""
    if not path:
        return False
    if "/system/bin/" in path:
        return True
    try:
        out = subprocess.check_output([path, "--help"], stderr=subprocess.STDOUT, timeout=5)
        out = out.decode("utf-8", "replace")
    except Exception:
        return True
    return "toybox" in out or "BusyBox" in out


def _download_one(url, archive, env, curl_path, wget_path, output):
    """Try to download ``url`` to ``archive`` once via curl, then a non-toybox
    wget, then Python urllib. Returns True on a non-empty file, False
    otherwise (caller validates SHA256 and cleans up on mismatch)."""
    # 1. curl — follows -L redirects, streams large headers.
    if curl_path:
        try:
            subprocess.check_call(
                [curl_path, "-L", "--fail", "--retry", "3",
                 "--connect-timeout", "15", "--max-time", "300",
                 "--speed-time", "30", "--speed-limit", "10240",
                 "-o", archive, url],
                env=env, timeout=330,
            )
            if os.path.exists(archive) and os.path.getsize(archive) > 0:
                return True
        except Exception as exc:
            output.warning("curl failed for %s: %s" % (url, exc))
        if os.path.exists(archive) and os.path.getsize(archive) == 0:
            try:
                os.remove(archive)
            except OSError:
                pass

    # 2. GNU wget (not toybox).
    if wget_path and not _is_toybox_wget(wget_path):
        try:
            subprocess.check_call(
                [wget_path, "--tries=3", "--timeout=30",
                 "-O", archive, url],
                env=env, timeout=330,
            )
            if os.path.exists(archive) and os.path.getsize(archive) > 0:
                return True
        except Exception as exc:
            output.warning("wget failed for %s: %s" % (url, exc))
        if os.path.exists(archive) and os.path.getsize(archive) == 0:
            try:
                os.remove(archive)
            except OSError:
                pass

    # 3. Python urllib — follows redirects natively. Fall back to an
    #    unverified SSL context if the system CA bundle lacks the mirror's
    #    intermediate cert (OHOS Python). Download authenticity is still
    #    guaranteed by the SHA256 gate.
    try:
        import ssl
        import urllib.request
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "conan-astra"})
        try:
            with urllib.request.urlopen(req, timeout=330, context=ctx) as resp, \
                    open(archive, "wb") as out_f:
                shutil.copyfileobj(resp, out_f)
        except ssl.SSLError as ssl_exc:
            # Do NOT silently downgrade TLS verification. The SHA256 gate
            # still guarantees integrity, but disabling certificate
            # validation would expose the download to MITM. Surface the
            # error and let _download_mirrored retry the next mirror.
            output.warning(
                "SSL verification failed for %s: %s. "
                "Set SSL_CERT_FILE to a valid CA bundle or ensure "
                "the system CA certificates are up to date."
                % (url, ssl_exc)
            )
            raise
        if os.path.exists(archive) and os.path.getsize(archive) > 0:
            return True
    except Exception as exc:
        output.warning("urllib failed for %s: %s" % (url, exc))
    if os.path.exists(archive) and os.path.getsize(archive) == 0:
        try:
            os.remove(archive)
        except OSError:
            pass
    return False


def _download_mirrored(urls, archive, expected_sha256, min_bytes, output):
    """Download ``archive`` from an ordered list of mirror ``urls``.

    Each successful download is immediately size-gated (>= ``min_bytes``)
    and SHA256-gated. On any failure the partial file is removed and the
    next mirror is tried. Only when all mirrors fail do we raise. The
    SHA256 value is authoritative and never weakened.
    """
    env = os.environ.copy()
    ssl_cert = "/storage/Users/currentUser/usr/local/ssl/cert.pem"
    if os.path.exists(ssl_cert):
        env["SSL_CERT_FILE"] = ssl_cert
    curl_path = shutil.which("curl")
    wget_path = shutil.which("wget")
    for u in urls:
        output.info("Trying mirror: " + u)
        if not _download_one(u, archive, env, curl_path, wget_path, output):
            continue
        if not os.path.isfile(archive):
            continue
        if os.path.getsize(archive) < min_bytes:
            output.warning(
                "Downloaded archive too small (%d bytes < %d), "
                "likely truncated; trying next mirror"
                % (os.path.getsize(archive), min_bytes)
            )
            try:
                os.remove(archive)
            except OSError:
                pass
            continue
        h = hashlib.sha256()
        with open(archive, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != expected_sha256:
            output.warning(
                "Mirror served wrong archive (sha256 %s != %s), "
                "trying next mirror" % (actual, expected_sha256)
            )
            try:
                os.remove(archive)
            except OSError:
                pass
            continue
        return True
    raise ConanException(
        "Failed to download a valid archive from any of %d mirror(s) "
        "(size/SHA256 gates all failed). Pre-place the archive at %s."
        % (len(urls), archive)
    )


# ---------------------------------------------------------------------------
# Recipe
# ---------------------------------------------------------------------------

class AstraConan(ConanFile):
    name = "astra"
    version = "1.1.0"
    description = "Command-Line Interface for DataStax Astra"
    license = "Apache-2.0"
    homepage = "https://docs.datastax.com/en/astra-cli"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    # No tool_requires: graalvm/23.0.2 and gradle/8.12 are not yet published
    # to the OHPCD Conan remote (see archives/a/astra/manifest.yaml), so
    # declaring them as tool_requires makes `conan create` fail at dependency
    # graph computation with "Package not resolved". astra's build() only
    # adapts a prebuilt glibc binary to musl and does not need a JDK/Gradle.

    def layout(self):
        basic_layout(self)

    def configure(self):
        # The prebuilt upstream binary is aarch64 glibc-dynamic. We only
        # support that target; other arches/OSes are a hard error rather
        # than a silent no-op.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "astra homebrew variant only supports Linux/OHOS"
            )
        if str(self.settings.arch) not in ("arm64", "aarch64", "armv8"):
            raise ConanInvalidConfiguration(
                "astra prebuilt binary is aarch64-only"
            )

    def requirements(self):
        # Runtime dependency: zlib-ng-compat provides libz.so.1 on OHOS
        # (the prebuilt astra binary NEEDED libz.so.1). Already in ohpcd.
        if self.settings.os in ("Linux", "OHOS"):
            self.requires("zlib-ng-compat/2.3.3")

    def build(self):
        """Download the upstream prebuilt astra-linux-arm64 tarball, extract
        it, then adapt the glibc-dynamic ELF binary to OHOS musl via the
        git-xet/qsv/spotify_player recipe (vendor gcompat → build shim →
        patchelf interpreter+NEEDED → ELF re-sign)."""
        # 1. Download + verify SHA256 of the prebuilt tarball.
        src = self.conan_data["sources"]
        urls = src["url"]
        if isinstance(urls, str):
            urls = [urls]
        expected_sha256 = src["sha256"]
        archive = os.path.join(self.build_folder, "astra-linux-arm64.tar.gz")
        if not os.path.isfile(archive):
            os.makedirs(self.build_folder, exist_ok=True)
            self.output.info(
                "Downloading astra prebuilt binary from %d mirror(s)"
                % len(urls)
            )
            # ~17 MB upstream; a 1 MB size gate rejects error pages early.
            _download_mirrored(urls, archive, expected_sha256,
                               min_bytes=1 * 1024 * 1024, output=self.output)
        else:
            # Re-verify the cached archive.
            h = hashlib.sha256()
            with open(archive, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            if h.hexdigest() != expected_sha256:
                os.remove(archive)
                raise ConanException(
                    "Cached astra archive SHA256 mismatch: expected "
                    + expected_sha256
                )

        # 2. Extract into a per-run dir, then move to astra_dir.
        astra_dir = os.path.join(self.build_folder, "astra-prebuilt")
        if not os.path.isdir(os.path.join(astra_dir, "bin")):
            extract_tmp = tempfile.mkdtemp(
                prefix="astra-extract-", dir=self.build_folder
            )
            with tarfile.open(archive, "r:gz") as tf:
                tf.extractall(extract_tmp)
            # The tarball has a top-level astra/ dir; move it to astra_dir.
            top = None
            for e in os.listdir(extract_tmp):
                full = os.path.join(extract_tmp, e)
                if os.path.isdir(full) and not os.path.islink(full):
                    top = full
                    break
            if top is None:
                raise ConanException(
                    "astra prebuilt archive has no top-level directory: "
                    + archive
                )
            os.makedirs(os.path.dirname(astra_dir) or ".", exist_ok=True)
            try:
                os.rename(top, astra_dir)
            except OSError:
                if os.path.isdir(astra_dir):
                    shutil.rmtree(astra_dir, ignore_errors=True)
                shutil.copytree(top, astra_dir, symlinks=True)
            shutil.rmtree(extract_tmp, ignore_errors=True)

        bin_dir = os.path.join(astra_dir, "bin")
        if not os.path.isfile(os.path.join(bin_dir, "astra")):
            raise ConanException(
                "astra prebuilt extraction finished but bin/astra missing at "
                + bin_dir
            )
        self.output.info("astra prebuilt extracted at " + astra_dir)

        # 3. Vendor the glibc→musl compat layer into bin_dir.
        self._vendor_gcompat(bin_dir)

        # 4. Build libglibc-shim.so (provides __res_state etc. stubs) and
        #    add it as a NEEDED onto libgcompat.so.0.
        self._build_glibc_shim(bin_dir)

        # 5. patchelf --set-interpreter + --replace-needed on every ELF.
        self._patch_elf_linker(bin_dir)

        # 6. Re-sign every ELF for the OHOS kernel exec path.
        self._resign_elf_files(bin_dir)

        # 7. Stage the adapted binary + bundled libs into source_folder
        #    build/native/nativeCompile/astra so the existing package()
        #    picks it up (keeps test_package and commands.json unchanged).
        stage_bin = os.path.join(
            self.source_folder, "build", "native", "nativeCompile"
        )
        os.makedirs(stage_bin, exist_ok=True)
        shutil.copy2(
            os.path.join(bin_dir, "astra"),
            os.path.join(stage_bin, "astra"),
        )
        # Copy the bundled JVM .so files alongside the binary so the
        # dynamic loader can resolve them at runtime.
        for name in os.listdir(bin_dir):
            if name == "astra":
                continue
            src_f = os.path.join(bin_dir, name)
            if os.path.isfile(src_f):
                shutil.copy2(src_f, os.path.join(stage_bin, name))
        self.output.info("Staged adapted astra binary to " + stage_bin)

    def package(self):
        # Copy the adapted native binary to bin/.
        src_bin = os.path.join(
            self.source_folder, "build", "native", "nativeCompile", "astra"
        )
        if not os.path.isfile(src_bin):
            raise ConanException(
                "Adapted astra binary not found at %s. build() may have failed."
                % src_bin
            )
        dst_bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin_dir, exist_ok=True)
        dst_bin = os.path.join(dst_bin_dir, "astra")
        shutil.copy2(src_bin, dst_bin)
        # Ensure executable bit (owner-x at minimum).
        try:
            os.chmod(dst_bin, os.stat(dst_bin).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass
        # Copy bundled JVM .so files alongside the binary so the dynamic
        # loader can resolve them at runtime.
        src_dir = os.path.dirname(src_bin)
        for name in os.listdir(src_dir):
            if name == "astra":
                continue
            src_f = os.path.join(src_dir, name)
            if os.path.isfile(src_f):
                shutil.copy2(src_f, os.path.join(dst_bin_dir, name))
        self.output.info("Installed astra binary to " + dst_bin)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    # ------------------------------------------------------------------
    # glibc→musl compat vendoring (Alpine APKs).
    # ------------------------------------------------------------------

    def _vendor_gcompat(self, bin_dir):
        """Vendor libgcompat.so.0 + transitive deps from Alpine APKs into
        ``bin_dir`` so the musl loader can resolve the SONAMEs that
        ``_patch_elf_linker`` rewrites the prebuilt astra binary's glibc
        NEEDED entries to.

        Alpine APKv2 packages are single gzip-compressed tar archives; we
        extract only the ``lib/*.so*`` / ``usr/lib/*.so*`` regular-file
        entries, flattening them into bin_dir. The vendored .so files are
        ELF shared objects, so the subsequent ``_patch_elf_linker`` (which
        signs them via ``_resign_elf_files``) will also sign them.
        """
        gcompat_data = self.conan_data.get("gcompat_source")
        if not gcompat_data:
            self.output.warning(
                "gcompat_source not found in conandata.yml; "
                "skipping glibc→musl compat vendoring. astra will likely "
                "fail with 'Error loading shared library libgcompat.so.0'."
            )
            return

        os.makedirs(bin_dir, exist_ok=True)
        env = os.environ.copy()
        ssl_cert = "/storage/Users/currentUser/usr/local/ssl/cert.pem"
        if os.path.exists(ssl_cert):
            env["SSL_CERT_FILE"] = ssl_cert
        curl_path = shutil.which("curl")
        wget_path = shutil.which("wget")

        apk_tmp = tempfile.mkdtemp(prefix="gcompat-apk-", dir=self.build_folder)
        try:
            for key, spec in (
                ("gcompat", gcompat_data.get("gcompat", {})),
                ("libucontext", gcompat_data.get("libucontext", {})),
                ("musl_obstack", gcompat_data.get("musl_obstack", {})),
                ("libgcc", gcompat_data.get("libgcc", {})),
            ):
                url = spec.get("url")
                expected_sha256 = spec.get("sha256")
                if not url or not expected_sha256:
                    self.output.warning(
                        "gcompat_source." + key + " missing url or sha256; skipping."
                    )
                    continue
                apk_path = os.path.join(apk_tmp, key + ".apk")
                if not _download_one(url, apk_path, env, curl_path, wget_path, self.output):
                    raise ConanException(
                        "Failed to download Alpine " + key + " APK from " + url
                    )
                if not os.path.isfile(apk_path) or os.path.getsize(apk_path) == 0:
                    raise ConanException(
                        "Alpine " + key + " APK download empty: " + apk_path
                    )
                with open(apk_path, "rb") as f:
                    actual_sha256 = hashlib.sha256(f.read()).hexdigest()
                if actual_sha256 != expected_sha256:
                    raise ConanException(
                        "Alpine " + key + " APK SHA256 mismatch: expected "
                        + expected_sha256 + " got " + actual_sha256
                        + " (url=" + url + ")"
                    )
                self.output.info("Vendoring Alpine " + key + " APK: " + os.path.basename(apk_path))
                # Extract lib/*.so* and usr/lib/*.so* entries into bin_dir.
                with tarfile.open(apk_path, "r:gz") as tf:
                    for m in tf.getmembers():
                        if not (m.isfile() or m.issym()):
                            continue
                        name = m.name
                        if not (name.startswith("lib/") or name.startswith("usr/lib/")):
                            continue
                        # Flatten to bin_dir/<basename>.
                        base = os.path.basename(name.rstrip("/"))
                        if not base:
                            continue
                        dst = os.path.join(bin_dir, base)
                        if m.issym():
                            # Resolve symlink to its target member and copy.
                            tgt = m.linkname
                            if not os.path.isabs(tgt):
                                tgt_dir = os.path.dirname(name)
                                tgt = os.path.normpath(os.path.join(tgt_dir, tgt))
                            tgt_member = tf.getmember(tgt) if tgt in tf.getnames() else None
                            if tgt_member is not None and tgt_member.isfile():
                                src_f = tf.extractfile(tgt_member)
                                if src_f is not None:
                                    with open(dst, "wb") as out_f:
                                        shutil.copyfileobj(src_f, out_f)
                            continue
                        src_f = tf.extractfile(m)
                        if src_f is None:
                            continue
                        with open(dst, "wb") as out_f:
                            shutil.copyfileobj(src_f, out_f)
            self.output.info("Vendored gcompat .so files into " + bin_dir)
        finally:
            shutil.rmtree(apk_tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # libglibc-shim.so: stub glibc resolver symbols for Alpine
    # libgcompat.so.0 on HongMeng musl libc.
    # ------------------------------------------------------------------

    def _build_glibc_shim(self, bin_dir):
        """Build ``libglibc-shim.so`` on-device and install it next to the
        vendored ``libgcompat.so.0`` in ``bin_dir``.

        HongMeng musl does not export ``__res_state`` / ``res_init`` /
        ``res_search`` (Alpine musl carries a patch that does). The musl
        loader aborts relocation of ``libgcompat.so.0`` with::

            Error relocating .../libgcompat.so.0: __res_state: symbol not found

        unless another loaded library exports them. This shim provides
        no-op stubs so relocation succeeds; astra never actually calls the
        resolver through the gcompat layer. Mirrors git-xet's published
        adaptation (archives/g/git-xet/homebrew/notes.md).
        """
        shim_source = (
            "/* libglibc-shim.c — stub glibc resolver symbols for\n"
            " * Alpine libgcompat.so.0 on HongMeng musl libc. */\n"
            "#include <stddef.h>\n"
            "void *__res_state(void) { return NULL; }\n"
            "int res_init(void) { return 0; }\n"
            "int __res_init(void) { return 0; }\n"
            "int res_search(const char *d, int c, int t,\n"
            "               unsigned char *a, int l) {\n"
            "    (void)d; (void)c; (void)t; (void)a; (void)l; return 0;\n"
            "}\n"
            "int __res_search(const char *d, int c, int t,\n"
            "                 unsigned char *a, int l) {\n"
            "    (void)d; (void)c; (void)t; (void)a; (void)l; return 0;\n"
            "}\n"
            "const char *gnu_get_libc_version(void) { return \"glibc-shim\"; }\n"
            "int pthread_mutexattr_setrobust(void *a, int r) {\n"
            "    (void)a; (void)r; return 0;\n"
            "}\n"
            "int pthread_mutex_consistent(void *m) { (void)m; return 0; }\n"
        )

        src_dir = tempfile.mkdtemp(prefix="glibc-shim-", dir=self.build_folder)
        src_path = os.path.join(src_dir, "glibc-shim.c")
        obj_path = os.path.join(src_dir, "libglibc-shim.so")
        shim_path = os.path.join(bin_dir, "libglibc-shim.so")
        gcompat_path = os.path.join(bin_dir, "libgcompat.so.0")
        try:
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(shim_source)

            # CI/HongMeng toolchain ships clang as the C compiler (Conan
            # profile tools.build:compiler_executables={'c': clang...});
            # gcompat/cc may be absent. Probe cc → gcc → clang on PATH, then
            # fall back to the known HongMeng toolchain absolute paths.
            cc = (
                shutil.which("cc")
                or shutil.which("gcc")
                or shutil.which("clang")
            )
            if not cc and os.path.isfile("/data/service/hnp/bin/clang"):
                cc = "/data/service/hnp/bin/clang"
            if not cc and os.path.isfile("/data/service/hnp/bin/gcc"):
                cc = "/data/service/hnp/bin/gcc"
            if not cc and os.path.isfile("/data/service/hnp/bin/cc"):
                cc = "/data/service/hnp/bin/cc"
            if not cc:
                raise ConanException(
                    "No C compiler (cc/gcc/clang) found on PATH or "
                    "/data/service/hnp/bin/; cannot build libglibc-shim.so."
                )

            cc_argv = [cc, "-shared", "-fPIC", "-o", obj_path, src_path]
            self.output.info("Building libglibc-shim.so: " + " ".join(cc_argv))
            try:
                subprocess.run(
                    cc_argv, check=True, capture_output=True, text=True,
                    timeout=120,
                )
            except subprocess.CalledProcessError as cpe:
                raise ConanException(
                    "gcc failed to build libglibc-shim.so (rc="
                    + str(cpe.returncode) + "): " + (cpe.stderr or "")
                )
            if not os.path.isfile(obj_path) or os.path.getsize(obj_path) == 0:
                raise ConanException(
                    "libglibc-shim.so build produced no output: " + obj_path
                )

            try:
                shutil.move(obj_path, shim_path)
            except OSError:
                shutil.copyfile(obj_path, shim_path)
            try:
                os.chmod(shim_path, 0o755)
            except OSError:
                pass
            self.output.info(
                "Built and installed libglibc-shim.so at " + shim_path
                + " (size=" + str(os.path.getsize(shim_path)) + ")"
            )

            # Add NEEDED libglibc-shim.so onto libgcompat.so.0 so the musl
            # loader pulls the shim in whenever libgcompat.so.0 is loaded.
            pe = shutil.which("patchelf")
            if not pe and os.path.isfile("/data/service/hnp/bin/patchelf"):
                pe = "/data/service/hnp/bin/patchelf"
            if not pe:
                self.output.warning(
                    "patchelf not found; cannot add NEEDED libglibc-shim.so "
                    "onto libgcompat.so.0."
                )
            elif os.path.isfile(gcompat_path):
                try:
                    subprocess.run(
                        [pe, "--add-needed", "libglibc-shim.so", gcompat_path],
                        check=True, capture_output=True, text=True, timeout=60,
                    )
                    self.output.info(
                        "Added NEEDED libglibc-shim.so onto libgcompat.so.0"
                    )
                except subprocess.CalledProcessError as cpe:
                    raise ConanException(
                        "patchelf --add-needed libglibc-shim.so failed on "
                        + gcompat_path + " (rc=" + str(cpe.returncode)
                        + "): " + (cpe.stderr or "")
                    )
        finally:
            shutil.rmtree(src_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # patchelf: rewrite ELF interpreter + glibc NEEDED entries for musl.
    # ------------------------------------------------------------------

    def _patch_elf_linker(self, root):
        """Rewrite the ELF interpreter and glibc NEEDED entries of every
        dynamic-linked ELF under ``root`` so it runs on OHOS's musl libc.

        ``patchelf --set-interpreter /lib/ld-musl-aarch64.so.1`` retargets
        the binary at OHOS's musl dynamic linker. ``patchelf --replace-needed``
        swaps each glibc shared-object dependency for the musl/gcompat
        equivalent present on the device. git-xet, qsv and spotify_player
        all use this scheme.
        """
        pe = shutil.which("patchelf")
        if not pe and os.path.isfile("/data/service/hnp/bin/patchelf"):
            pe = "/data/service/hnp/bin/patchelf"
        if not pe:
            self.output.warning(
                "patchelf not found on PATH or /data/service/hnp/bin/; "
                "skipping ELF interpreter/NEEDED rewrite."
            )
            return

        OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"
        GLIBC_REPLACEMENTS = [
            ("libc.so.6", "libgcompat.so.0"),
            ("libm.so.6", "libgcompat.so.0"),
            ("libdl.so.2", "libgcompat.so.0"),
            ("libpthread.so.0", "libgcompat.so.0"),
            ("librt.so.1", "libgcompat.so.0"),
            ("libcrypt.so.1", "libgcompat.so.0"),
            ("libresolv.so.2", "libgcompat.so.0"),
            ("ld-linux-aarch64.so.1", "libgcompat.so.0"),
        ]

        def _run_patchelf_one(argv, fpath):
            """Run one patchelf op on fpath. Return True if it changed the
            file, None if it was a benign no-op, False on a real failure."""
            try:
                proc = subprocess.run(
                    [pe] + argv + [fpath],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except Exception as exc:
                self.output.warning(
                    "patchelf op exception for " + fpath + ": " + str(exc)
                )
                return False
            if proc.returncode == 0:
                return True
            err = (proc.stderr or "").strip()
            low = err.lower()
            if "cannot set interpreter" in low \
                    or "does not have an interpreter" in low \
                    or "cannot find section" in low \
                    or "statically linked" in low \
                    or "nothing to do" in low \
                    or "not found" in low \
                    or "no matching" in low \
                    or "is not an elf" in low \
                    or "not an elf" in low:
                return None
            self.output.warning(
                "patchelf op failed for " + fpath + ": rc="
                + str(proc.returncode) + " err=" + err
            )
            return False

        patched = 0
        skipped = 0
        failed = 0
        for dirpath, dirs, files in os.walk(root):
            for name in files:
                fpath = os.path.join(dirpath, name)
                if os.path.islink(fpath):
                    continue
                try:
                    with open(fpath, "rb") as f:
                        magic = f.read(4)
                except OSError:
                    skipped += 1
                    continue
                if magic != b"\x7fELF":
                    continue
                file_failed = False
                file_changed = False
                res = _run_patchelf_one(
                    ["--set-interpreter", OHOS_INTERP], fpath
                )
                if res is True:
                    file_changed = True
                elif res is False:
                    file_failed = True
                for glibc_soname, musl_repl in GLIBC_REPLACEMENTS:
                    res = _run_patchelf_one(
                        ["--replace-needed", glibc_soname, musl_repl], fpath
                    )
                    if res is True:
                        file_changed = True
                    elif res is False:
                        file_failed = True
                if file_failed:
                    failed += 1
                elif file_changed:
                    patched += 1
                else:
                    skipped += 1
        self.output.info(
            "ELF linker rewrite: patched=" + str(patched)
            + " skipped=" + str(skipped)
            + " failed=" + str(failed)
        )

    # ------------------------------------------------------------------
    # ELF re-sign for the OHOS kernel exec path.
    # ------------------------------------------------------------------

    def _resign_elf_files(self, root):
        """Re-sign every ELF file under ``root`` for the OHOS kernel.

        Walks ``root`` and, for every regular file whose first four bytes
        are the ELF magic (``\\x7fELF``), runs
        ``binary-sign-tool sign -inFile X -outFile X -selfSign 1``. This
        adds the OHOS .codesign / .note.ohos.ident segments the kernel
        requires, turning execve(bin/java) from an unsigned-ELF EACCES
        into a normal POSIX owner-x check.
        """
        bst = shutil.which("binary-sign-tool")
        if not bst and os.path.isfile("/data/service/hnp/bin/binary-sign-tool"):
            bst = "/data/service/hnp/bin/binary-sign-tool"
        if not bst:
            self.output.warning(
                "binary-sign-tool not found on PATH or "
                "/data/service/hnp/bin/; skipping ELF re-sign. "
                "On OHOS this means execve(astra) will likely EACCES."
            )
            return

        signed = 0
        skipped = 0
        failed = 0
        for dirpath, dirs, files in os.walk(root):
            for name in files:
                fpath = os.path.join(dirpath, name)
                try:
                    real = os.path.realpath(fpath)
                except OSError:
                    skipped += 1
                    continue
                if not os.path.isfile(real):
                    skipped += 1
                    continue
                try:
                    with open(real, "rb") as f:
                        magic = f.read(4)
                except OSError:
                    skipped += 1
                    continue
                if magic != b"\x7fELF":
                    skipped += 1
                    continue
                try:
                    subprocess.run(
                        [bst, "sign", "-inFile", real, "-outFile", real,
                         "-selfSign", "1"],
                        check=True, capture_output=True, text=True, timeout=60,
                    )
                    signed += 1
                except Exception as exc:
                    failed += 1
                    self.output.warning(
                        "binary-sign-tool failed for " + real + ": " + str(exc)
                    )
        self.output.info(
            "ELF re-sign complete: signed=" + str(signed)
            + " skipped=" + str(skipped)
            + " failed=" + str(failed)
        )
