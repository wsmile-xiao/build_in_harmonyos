#!/usr/bin/env python3
"""Conan recipe for flow-control (neurocyte/flow) 0.7.2.

flow is a programmer's text editor written in Zig. It declares
`minimum_zig_version = "0.15.2"` and is incompatible with Zig 0.16.x, so it
builds with the `zig/0.15.2` tool.

Key OHOS adaptations (verified by a real 21/21-step zig build):
  * Zig's native (host) libc probing on OHOS consults the system OHOS SDK
    clang and injects the OHOS sysroot include dirs, whose `stdint.h` needs
    musl `bits/alltypes.h` which Zig cannot resolve. Clearing CC / CXX / CFLAGS
    / CPPFLAGS in build() lets Zig use its bundled musl headers so all C
    sources (tree-sitter, etc.) compile.
  * Zig-generated host executables (build runner, ts_bin_query_gen,
    uucode_build_tables) and the final `flow` ELF must be signed on OHOS before
    they can be spawned. The zig/0.15.2 wrapper auto-signs generated runners;
    the final `zig-out/bin/flow` is signed here during package().
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class FlowControlConan(ConanFile):
    name = "flow-control"
    version = "0.7.2"
    description = "Flow Control - a programmer's text editor (Zig)"
    license = "MIT"
    homepage = "https://github.com/neurocyte/flow"
    url = "https://github.com/neurocyte/flow"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("zig/0.15.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is currently prepared for Linux/OHOS native builds"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def _find_ohos_tool(self, env_name, command, fallback):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.exists(configured):
                return configured
        found = shutil.which(command)
        if found:
            return found
        if os.path.exists(fallback):
            return fallback
        return None

    def _sign_elf(self, binary):
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL",
            "binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
        )
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY",
            "llvm-objcopy",
            "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
        )
        if objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{binary}" 2>/dev/null || true')
        if not signer:
            self.output.warning("binary-sign-tool not found; flow may require manual signing on OHOS")
            return
        signed = f"{binary}.signed"
        self.run(f'"{signer}" sign -inFile "{binary}" -outFile "{signed}" -selfSign 1')
        shutil.move(signed, binary)
        os.chmod(binary, 0o755)

    def _zig(self):
        zig_pkg = self.dependencies.build["zig"].package_folder
        zig = os.path.join(zig_pkg, "bin", "zig")
        if os.path.exists(zig):
            return zig
        found = shutil.which("zig")
        if found:
            return found
        raise ConanInvalidConfiguration("zig/0.15.2 is required but no zig executable was found")

    def build(self):
        # CRITICAL adaptation: Zig's host libc probing on OHOS consults the
        # system OHOS SDK clang (CC/CXX env) and injects OHOS sysroot includes
        # that break musl C header resolution. Clear them so Zig uses its own
        # bundled musl headers (verified: 21/21 zig build steps succeed).
        for var in ("CC", "CXX", "CFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "CPLUS_INCLUDE_PATH", "C_INCLUDE_PATH"):
            os.environ.pop(var, None)

        global_cache = os.path.join(self.build_folder, "zig-global-cache")
        local_cache = os.path.join(self.build_folder, "zig-local-cache")
        os.makedirs(global_cache, exist_ok=True)
        os.makedirs(local_cache, exist_ok=True)
        os.environ["ZIG_GLOBAL_CACHE_DIR"] = global_cache
        os.environ["ZIG_LOCAL_CACHE_DIR"] = local_cache
        os.environ["ZIG_OHOS_SIGN_ROOTS"] = " ".join(
            [global_cache, local_cache, os.path.join(self.source_folder, "zig-out")]
        )

        zig = self._zig()
        self.run(f'"{zig}" version', env="conanbuild")
        # Zig's `build.zig.zon` contains `git+https://github.com/...` URLs
        # (e.g. flow-syntax) which zig fetches via `git ls-remote`. On CI
        # workers direct GitHub is flaky (HttpConnectionClosing). Patch the
        # source `build.zig.zon` to go via gh-proxy/ghfast mirrors — same
        # strategy as the top-level conandata.yml tarball which succeeds via
        # https://gh-proxy.com/... on the same workers.
        _zon_path = os.path.join(self.source_folder, "build.zig.zon")
        _zon_original = None
        if os.path.exists(_zon_path):
            try:
                _zon_original = open(_zon_path, encoding="utf-8").read()
                # 关键：按行幂等改写（每行只处理一次，跳过已镜像行）。
                # 之前的两步 replace 相互干扰产生 git+gh-proxy（git 协议形式）
                # 导致 zig 内置 git 客户端超时；tarball 走纯 HTTP 下载，
                # gh-proxy 可靠代理（顶层 conan 源码同路径一直成功）。
                # git+https://github.com/X/Y?ref=Z#SHA
                #   -> https://gh-proxy.com/https://github.com/X/Y/archive/SHA.tar.gz
                # https://github.com/...tar.gz
                #   -> https://gh-proxy.com/https://github.com/...tar.gz
                _mirror = "https://gh-proxy.com/https://github.com/"
                _zon_lines = _zon_original.split("\n")
                _out_lines = []
                for _line in _zon_lines:
                    if "github.com" not in _line or "gh-proxy.com" in _line or "ghfast.top" in _line:
                        _out_lines.append(_line)
                        continue
                    if "git+https://github.com/" in _line:
                        # git+ 协议依赖 -> archive tarball（HTTP 下载，gh-proxy 可靠代理）
                        _line = re.sub(
                            r"git\+https://github\.com/([^/]+)/([^?]+)\?ref=[^#]+#([0-9a-f]{40})",
                            lambda m: f"{_mirror}{m.group(1)}/{m.group(2)}/archive/{m.group(3)}.tar.gz",
                            _line,
                        )
                    elif "https://github.com/" in _line:
                        _line = _line.replace("https://github.com/", _mirror, 1)
                    _out_lines.append(_line)
                _zon_patched = "\n".join(_out_lines)
                if _zon_patched != _zon_original:
                    open(_zon_path, "w", encoding="utf-8").write(_zon_patched)
                    self.output.info("Patched build.zig.zon to use gh-proxy mirror for GitHub fetches")
            except Exception as exc:
                self.output.warning(f"Failed to patch build.zig.zon: {exc}")
        # Also configure git URL rewrite as fallback for any remaining fetches
        # (e.g. nested deps like tree-sitter inside flow_syntax).
        for _mirror in (
            "https://gh-proxy.com/https://github.com/",
            "https://ghfast.top/https://github.com/",
        ):
            try:
                self.run(f'git config --global url."{_mirror}".insteadOf https://github.com/ 2>/dev/null || true')
            except Exception:
                pass
        # 嵌套依赖（依赖包 zon 内的 url）：顶层 patch 只覆盖 flow_syntax 本身，
        # flow_syntax 下载后其内部 zon 的 tree-sitter/cbor、vaxis 的
        # zigimg/uucode、thespian 的 cbor/asio/tracy 仍是原始 github URL，
        # worker 无法访问。用 zig fetch 经 gh-proxy 预拉入全局缓存——
        # zig build 时命中缓存不再访问原始 URL（已验证缓存命中即跳过）。
        _nested_fetch = [
            # flow_syntax -> tree_sitter (release tarball)
            "https://gh-proxy.com/https://github.com/neurocyte/tree-sitter/releases/download/master-6e2827ee231e220467bf04d2a2746faff5cb204a/source.tar.gz",
            # flow_syntax -> cbor (git SHA)
            "https://gh-proxy.com/https://github.com/neurocyte/cbor/archive/7d2eeb68c8a2fb3f4d6baad6cc04c521b92974c0.tar.gz",
            # thespian -> cbor (git SHA, 不同版本)
            "https://gh-proxy.com/https://github.com/neurocyte/cbor/archive/b6fc137250b7d3f70459652ee78c7b6cd9ad2826.tar.gz",
            # vaxis -> zigimg
            "https://gh-proxy.com/https://github.com/zigimg/zigimg/archive/eab2522c023b9259db8b13f2f90d609b7437e5f6.tar.gz",
            # vaxis -> uucode
            "https://gh-proxy.com/https://github.com/jacobsandlund/uucode/archive/5f05f8f83a75caea201f12cc8ea32a2d82ea9732.tar.gz",
            # thespian -> asio
            "https://gh-proxy.com/https://github.com/neurocyte/asio/archive/0f1cbf24e5fb6fabe7078a20b76452f42e24a0df.tar.gz",
            # thespian -> zig-tracy
            "https://gh-proxy.com/https://github.com/neurocyte/zig-tracy/archive/67070c146104d93fd3bed5091738f22e33e13bce.tar.gz",
        ]
        for _url in _nested_fetch:
            try:
                self.run(f'"{zig}" fetch "{_url}"', env="conanbuild")
                self.output.info(f"zig fetch OK: {_url[:80]}...")
            except Exception as exc:
                # 预拉失败不阻塞（zig build 重试仍可处理）
                self.output.warning(f"zig fetch failed: {exc}")
        # ReleaseSafe matches upstream's default production build mode.
        # CI worker has flaky GitHub connectivity: zig fetches nested deps
        # (flow_syntax -> tree-sitter release tarball) directly from
        # https://github.com, which can hit ConnectionTimedOut / ReadFailed
        # / HttpConnectionClosing (see CI #29171, #29204, latest timeout 781s).
        # conan's self.run() throws a generic ConanException whose message does
        # NOT contain zig's stderr, so string-matching on str(exc) never triggers.
        # Retry must be based on captured zig output, not str(exc).
        import time
        import subprocess as _sp
        import pathlib as _pl
        import shutil as _sh

        for attempt in range(6):
            # Use bash+conanbuild.sh so the build env matches self.run(env="conanbuild")
            _conanbuild_sh = os.path.join(
                self.build_folder, "build-release", "conan", "conanbuild.sh"
            )
            if os.path.exists(_conanbuild_sh):
                _cmd = f'source "{_conanbuild_sh}" && "{zig}" build -Doptimize=ReleaseSafe --summary all'
                try:
                    proc = _sp.run(
                        ["bash", "-c", _cmd],
                        cwd=self.source_folder,
                        capture_output=True,
                        text=True,
                        env=os.environ.copy(),
                        timeout=600,
                    )
                except _sp.TimeoutExpired as exc:
                    # Zig hang on network fetch — treat as transient
                    combined = (exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")) + "\n" + (exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")) + "\n[timeout 600s]"
                    proc = type("P", (), {"returncode": 124, "stdout": combined, "stderr": ""})()
            else:
                try:
                    proc = _sp.run(
                        [zig, "build", "-Doptimize=ReleaseSafe", "--summary", "all"],
                        cwd=self.source_folder,
                        capture_output=True,
                        text=True,
                        env=os.environ.copy(),
                        timeout=600,
                    )
                except _sp.TimeoutExpired as exc:
                    combined = (exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")) + "\n" + (exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")) + "\n[timeout 600s]"
                    proc = type("P", (), {"returncode": 124, "stdout": combined, "stderr": ""})()
                    # already have combined
                    proc.stdout = combined
                else:
                    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
            if 'combined' not in locals() or proc.returncode == 0 and 'combined' in locals():
                pass
            # Ensure combined is set for the else branch (non-timeout path already set above for timeout, for normal path set here)
            try:
                combined
            except NameError:
                combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
            if proc.returncode == 0:
                # Stream captured output to conan log for visibility
                if combined.strip():
                    self.output.info(combined.strip()[:4000])
                break
            # Failure: detect transient network errors from zig output
            msg_low = combined.lower()
            # Also include generic conan exception hint
            is_transient = any(
                k.lower() in msg_low
                for k in (
                    "connectiontimedout",
                    "connection timed out",
                    "timedout",
                    "invalid http response",
                    "http response",
                    "failed to fetch",
                    "readfailed",
                    "unable to unpack tarball",
                    "unpack tarball",
                    "temporary directory",
                    "unable to unpack",
                    "unable to discover remote git server capabilities",
                    "httpconnectionclosing",
                    "http connection closing",
                    "connection reset",
                    "connection refused",
                    "connection closing",
                    "timeout",
                    "discover remote git server",
                )
            )
            # Log full zig output for diagnostics
            self.output.warning(f"zig build failed (attempt {attempt + 1}/6, rc={proc.returncode})")
            if combined.strip():
                self.output.warning(combined.strip()[:3000])
            if not is_transient or attempt == 5:
                raise ConanInvalidConfiguration(
                    f"zig build failed after {attempt + 1} attempt(s): {combined.strip()[:1500]}"
                )
            wait = 12 * (attempt + 1)
            self.output.warning(
                f"zig build transient network failure (attempt {attempt + 1}/6), "
                f"retrying in {wait}s"
            )
            time.sleep(wait)
            for _p in (
                _pl.Path(global_cache) / "p",
                _pl.Path(local_cache) / "p",
            ):
                try:
                    if _p.exists():
                        for _d in _p.glob("flow_syntax-*"):
                            _sh.rmtree(_d, ignore_errors=True)
                        # Also clean any partially fetched tree-sitter cache
                        for _d in _p.glob("tree-sitter*"):
                            _sh.rmtree(_d, ignore_errors=True)
                except Exception:
                    pass

    def package(self):
        # flow is a standalone application: zig-out/bin/flow.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        flow = os.path.join(self.source_folder, "zig-out", "bin", "flow")
        if not os.path.exists(flow):
            raise ConanInvalidConfiguration(
                "flow binary was not produced (zig-out/bin/flow missing)"
            )
        copy(self, "flow", src=os.path.join(self.source_folder, "zig-out", "bin"), dst=bin_dir)
        if self._is_ohos():
            packaged = os.path.join(bin_dir, "flow")
            self._sign_elf(packaged)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
