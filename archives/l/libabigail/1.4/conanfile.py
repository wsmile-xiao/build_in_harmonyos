#!/usr/bin/env python3
"""Conan recipe — libabigail 1.4 (autotools)

The ABI Generic Analysis and Instrumentation Library (libabigail) from
Red Hat, built natively for HarmonyOS PC (aarch64) with clang/libc++.

OHOS 适配要点：
- config.guess/config.sub 补丁识别 aarch64-unknown-linux-ohos（E007）
- configure umask 077→022 规避 HMDFS setgid 临时目录写入失败（E129）
- tr1/* → std/* 现代化（libc++ 无 <tr1/...>）
- temp_file 使用 std::fstream + TMPDIR（libc++ 无 __gnu_cxx::stdio_filebuf；/tmp 只读 E002）
- 依赖 libelf/libdw（elfutils）、libxml2、fts（musl-fts）经 CPPFLAGS/LDFLAGS/LIBS 喂给 configure
- ~150MB 源包：权威镜像 URL 列表 + 慢速/中断失败切换（同 linux-headers，避免吃满 CI 2700s）
"""
import glob
import hashlib
import os
import shutil
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, unzip
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibabigailConan(ConanFile):
    name = "libabigail"
    version = "1.4"
    description = "The ABI Generic Analysis and Instrumentation Library (libabigail)"
    license = "LGPL-3.0-or-later"
    homepage = "https://sourceware.org/libabigail/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libxml2: XML 解析；elfutils: libelf/libdw（configure 需 libelf.h/-lelf/-ldw）
        # musl-fts: 提供 fts.h/libfts（OHOS 无系统 fts）
        self.requires("libxml2/2.15.3")
        self.requires("elfutils/0.195")
        self.requires("musl-fts/1.2.7")

    def layout(self):
        basic_layout(self, src_folder=".")

    @staticmethod
    def _source_filename(url):
        return os.path.basename(urlparse(url).path)

    def _candidate_source_urls(self):
        urls = self.conan_data["sources"]["url"]
        if isinstance(urls, str):
            return [urls]
        return list(urls)

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _download_cache_dir(self):
        cache = os.environ.get("DOWNLOAD_CACHE")
        if cache:
            try:
                os.makedirs(cache, exist_ok=True)
                return cache
            except OSError as exc:
                self.output.warning(f"DOWNLOAD_CACHE is not usable: {exc}")
        return self.source_folder

    def _cache_path_for(self, url):
        return os.path.join(self._download_cache_dir(), self._source_filename(url))

    def _cached_archive(self, sha256):
        for url in self._candidate_source_urls():
            path = self._cache_path_for(url)
            if os.path.isfile(path):
                actual = self._sha256(path)
                if actual == sha256:
                    self.output.info(f"Using cached source archive: {path}")
                    return path
                self.output.warning(
                    f"Ignoring cached archive with unexpected sha256: {path}"
                )
        return None

    @staticmethod
    def _env_int(name, default, minimum):
        raw_value = os.environ.get(name, str(default))
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ConanException(
                f"{name} must be an integer, got {raw_value!r}"
            ) from exc
        if value < minimum:
            raise ConanException(
                f"{name} must be at least {minimum}, got {raw_value!r}"
            )
        return value

    @classmethod
    def _download_settings(cls):
        # Abort slow mirrors early so CI 2700s budget is not spent on ~10KB/s links.
        return (
            cls._env_int("OHPCD_SOURCE_MAX_SECONDS", 900, 1),
            cls._env_int("OHPCD_SOURCE_MIN_BYTES_PER_SECOND", 65536, 1),
            cls._env_int("OHPCD_SOURCE_MIN_RATE_GRACE", 90, 0),
            cls._env_int("OHPCD_SOURCE_READ_TIMEOUT", 30, 1),
        )

    def _download_archive(self, url, destination, sha256):
        max_seconds, min_rate, grace, read_timeout = self._download_settings()
        tmp = f"{destination}.part"
        digest = hashlib.sha256()
        downloaded = 0
        started = time.monotonic()
        last_report = started

        self.output.info(
            f"Downloading {url} with bounded source fallback "
            f"(max {max_seconds}s per URL, min {min_rate} B/s after {grace}s)"
        )
        request = Request(url, headers={"User-Agent": "ohpcd-conan-source/1.0"})
        try:
            with urlopen(request, timeout=read_timeout) as response:
                with open(tmp, "wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        now = time.monotonic()
                        elapsed = max(now - started, 0.001)
                        if now - last_report >= 30 or downloaded % (8 * 1024 * 1024) < len(chunk):
                            self.output.info(
                                f"Downloaded {downloaded // 1024}KB from "
                                f"{urlparse(url).netloc}"
                            )
                            last_report = now
                        if elapsed > max_seconds:
                            raise ConanException(
                                f"source download exceeded {max_seconds}s for {url}"
                            )
                        if elapsed > grace and downloaded / elapsed < min_rate:
                            raise ConanException(
                                "source download too slow for CI timeout "
                                f"({int(downloaded / elapsed)} B/s) from {url}"
                            )
            actual = digest.hexdigest()
            if actual != sha256:
                raise ConanException(
                    f"source archive sha256 mismatch for {url}: "
                    f"expected {sha256}, got {actual}"
                )
            os.replace(tmp, destination)
            return destination
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _fetch_source_archive(self):
        sha256 = self.conan_data["sources"]["sha256"]
        cached = self._cached_archive(sha256)
        if cached:
            return cached

        errors = []
        for url in self._candidate_source_urls():
            destination = self._cache_path_for(url)
            try:
                return self._download_archive(url, destination, sha256)
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                self.output.warning(f"Source URL failed, trying next: {exc}")
        raise ConanException(
            "All source URLs failed:\n" + "\n".join(errors)
        )

    def source(self):
        # Prefer DOWNLOAD_CACHE + mirror failover; plain get() will sit on a slow
        # single URL until the outer 2700s conan create timeout (CI #13300).
        archive = self._fetch_source_archive()
        unzip(self, archive, destination=self.source_folder, strip_root=True)

    @staticmethod
    def _abs_dep_paths(dep, rel_paths):
        """Resolve cpp_info dirs to absolute paths under package_folder.

        Conan often yields relative 'lib'/'include'. os.path.join('', 'lib') is
        still 'lib' — CI #13333/#14253 kept -Llib in LDFLAGS and AC_PROG_CXX
        failed with 'C++ compiler cannot create executables'. Skip deps without
        package_folder; keep only existing absolute directories (gd/2.3.3 pattern).
        """
        root = getattr(dep, "package_folder", None) or ""
        if not root:
            return []
        out = []
        for path in rel_paths or []:
            if not path:
                continue
            full = path if os.path.isabs(path) else os.path.join(root, path)
            if os.path.isdir(full):
                out.append(full)
        return out

    @staticmethod
    def _drop_relative_dash_flags(flags):
        """Remove -I/-L entries whose path is not absolute (inherited env noise)."""
        kept = []
        for tok in (flags or "").split():
            if tok.startswith(("-I", "-L")) and len(tok) > 2:
                if not os.path.isabs(tok[2:]):
                    continue
            kept.append(tok)
        return " ".join(kept)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS 适配版 conan 的 AutotoolsToolchain 将 --prefix 设为
        # "<conan package>" 占位符但 Autotools.configure() 未替换它，
        # 导致 configure 失败。显式追加 --prefix=/ 覆盖（configure 取最后值）。
        tc.configure_args.append("--prefix=/")

        # 依赖路径：只喂绝对 -I/-L（及 LD_LIBRARY_PATH）。
        # CI #14152：-Llib 已清掉后仍 AC_PROG_CXX 失败，因为 LIBS 预填了
        # -lxml2 -lelf -ldw …，探测阶段把「空程序」链上整棵依赖树而失败。
        # AC_CHECK_LIB / PKG_CHECK_MODULES 会自己追加 -l*；configure 不探测的
        # -lfts 单独保留。libxml 走 PkgConfigDeps（与 librrd/gd 同法）。
        _inc, _lib, _ldpath = [], [], []
        for _dep in self.dependencies.host.values():
            ci = _dep.cpp_info
            for _p in self._abs_dep_paths(_dep, ci.includedirs):
                _inc.append("-I" + _p)
            for _p in self._abs_dep_paths(_dep, ci.libdirs):
                _lib.append("-L" + _p)
                _ldpath.append(_p)

        base_cpp = self._drop_relative_dash_flags(os.environ.get("CPPFLAGS", ""))
        base_ld = self._drop_relative_dash_flags(os.environ.get("LDFLAGS", ""))
        os.environ["CPPFLAGS"] = (" ".join(_inc) + " " + base_cpp).strip()
        os.environ["LDFLAGS"] = (" ".join(_lib) + " " + base_ld).strip()
        # 仅 -lfts：其余由 AC_CHECK_LIB / pkg-config 在探测通过后再加
        os.environ["LIBS"] = "-lfts"
        _ldpath = [p for p in _ldpath if os.path.isabs(p)]
        os.environ["CPPFLAGS"] = self._drop_relative_dash_flags(os.environ["CPPFLAGS"])
        os.environ["LDFLAGS"] = self._drop_relative_dash_flags(os.environ["LDFLAGS"])
        # E120/E132 / openblas·morpheus：OHOS SDK 的 lld 运行时依赖 llvm/lib 里的
        # libxml2.so.16。若 LD_LIBRARY_PATH 先放 Conan libxml2，lld 会加载错库并
        # 报 xmlFreeDoc symbol not found（CI #14268）。必须把 SDK llvm/lib 置顶。
        sdk_llvm_libs = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
        )
        sdk_llvm_lib = sdk_llvm_libs[-1] if sdk_llvm_libs else ""
        ld_parts = []
        if sdk_llvm_lib and os.path.isdir(sdk_llvm_lib):
            ld_parts.append(sdk_llvm_lib)
        ld_parts.extend(_ldpath)
        # 保留原 LD_LIBRARY_PATH 中非重复项，但不得排到 SDK 之前
        seen = set(ld_parts)
        for part in os.environ.get("LD_LIBRARY_PATH", "").split(":"):
            if part and part not in seen:
                ld_parts.append(part)
                seen.add(part)
        os.environ["LD_LIBRARY_PATH"] = ":".join(ld_parts)
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"][:200])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"][:200])
        self.output.info("LIBS=%s" % os.environ["LIBS"][:200])
        self.output.info("LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"][:200])
        if " -Llib" in f" {os.environ['LDFLAGS']} " or os.environ["LDFLAGS"].endswith("-Llib"):
            raise ConanException(
                "LDFLAGS still contains relative -Llib after sanitization; "
                "refusing to configure (would fail AC_PROG_CXX)"
            )
        PkgConfigDeps(self).generate()
        tc.generate()
        env = Environment()
        env.define("CPPFLAGS", os.environ["CPPFLAGS"])
        env.define("LDFLAGS", os.environ["LDFLAGS"])
        env.define("LIBS", os.environ["LIBS"])
        env.define("LD_LIBRARY_PATH", os.environ["LD_LIBRARY_PATH"])
        # PKG_CONFIG_PATH：PkgConfigDeps 写到 generators_folder
        gen = self.generators_folder
        prev_pc = os.environ.get("PKG_CONFIG_PATH", "")
        pc = gen if not prev_pc else f"{gen}:{prev_pc}"
        os.environ["PKG_CONFIG_PATH"] = pc
        env.define("PKG_CONFIG_PATH", pc)
        env.vars(self).save_script("zz_libabigail_depflags")

    def build(self):
        apply_conandata_patches(self)
        # ⚠️ umask 077→022：HMDFS 新建目录固定 setgid，umask 077 会让
        # configure/config.status 临时目录对 owner 都不可写（E129）。
        # configure 是生成的，patch 可能因 autoreconf 再生成而失效，
        # 故在 build() 里幂等地再刷一遍（与 elfutils/0.195 同法）。
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                              recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            cfg_log = os.path.join(self.build_folder, "config.log")
            if os.path.isfile(cfg_log):
                try:
                    with open(cfg_log, encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                    # Prefer the failed CXX smoke-test snippet over the trailing dump.
                    marker = "checking whether the C++ compiler works"
                    idx = text.rfind(marker)
                    if idx < 0:
                        idx = text.rfind("failed program was")
                    snippet = text[idx:idx + 3500] if idx >= 0 else text[-4000:]
                    self.output.error("config.log (cxx probe):\n" + snippet)
                except OSError:
                    pass
            raise
        # 默认并行：CI 2700s 预算下 -j1 易超时；本地验证 -j20 约 2–3 分钟。
        # 仍可用 -c tools.build:jobs=N 覆盖。
        _jobs = int(
            self.conf.get(
                "tools.build:jobs",
                default=min(os.cpu_count() or 4, 20),
            )
        )
        autotools.make(args=[f"-j{_jobs}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        # Prefer PATH / compiler dir; fall back to CI HNP bin (same layout as elfutils).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("c") or compilers.get("cpp") or "")
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            shutil.which(name) or "",
            os.path.join("/data/service/hnp/bin", name),
        ]
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名
        # （与 elfutils/libxml2 配方同法：conan install 复制会破坏链接器自签）。
        import glob as _glob
        targets = _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"),
                             recursive=True)
        targets += _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"),
                              recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "llvm-objcopy/binary-sign-tool not found; skip codesign"
            )
            return
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["abigail"]
        # CLI tools (abidw/abidiff/…) install to bin/; required for R38 commands.json
        self.cpp_info.bindirs = ["bin"]
        # 头文件装在 <pkg>/include/libabigail/*.h（见安装出的 libabigail.pc）
        self.cpp_info.includedirs = ["include/libabigail"]
        self.cpp_info.set_property("pkg_config_name", "libabigail")
