#!/usr/bin/env python3
"""Conan recipe for aws-crt 0.38.5 — AWS Common Runtime C++ distribution
(awslabs/aws-crt-cpp v0.38.5, the umbrella release of the AWS CRT for C++).

Source layout: the upstream GitHub tag tarball does NOT contain git submodule
content, so the 13 crt/* submodules pinned by v0.38.5 are downloaded and
extracted separately in source() (commit hashes verified against the tag).

Build layout: BUILD_DEPS=ON (upstream default) compiles the full AWS CRT
stack — aws-lc (libcrypto), s2n-tls and every aws-c-* library — from the
vendored sources, then links libaws-crt-cpp on top.

OHOS adaptations:
  - aws-c-io only recognizes CMAKE_SYSTEM_NAME "Linux"/"Android" for its
    epoll event loop; Conan's toolchain maps os=OHOS to "HarmonyOS". We force
    CMAKE_SYSTEM_NAME=Linux (OHOS is a Linux-compatible musl platform).
  - ENFORCE_SUBMODULE_VERSIONS=OFF: release tarball has no git repo.
  - Upstream unit tests run inside build() via ctest:
      * patch 0002 keeps add_subdirectory(tests) reachable although a
        toolchain-based build always has CMAKE_CROSSCOMPILING=TRUE;
      * ENABLE_NET_TESTS=OFF removes every network-dependent registration;
      * patch 0003 moves the one env-gated IoT case out of offline discovery.
    The machine-readable evidence marker HMBS_UPSTREAM_TEST_RESULT is printed
    with counts parsed from ctest output, and the same JSON is packaged as
    res/upstream_test_result.json so test_package can re-emit it even when a
    cached package skips build().
"""
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import tarfile
import tempfile
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AwsCrtConan(ConanFile):
    name = "aws-crt"
    version = "0.38.5"
    description = (
        "AWS Common Runtime C++ 库（aws-crt-cpp 发行版）：MQTT5/MQTT311、HTTP、"
        "IoT、S3、Sigv4 签名、CBOR、校验和等异步客户端运行时"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-crt-cpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无外部 Conan 依赖：全部 AWS C 运行时组件（aws-lc、s2n、aws-c-*）
        # 以 v0.38.5 锁定的子模块源码随主库一起编译（BUILD_DEPS=ON）。
        pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanException(
                f"aws-crt recipe targets Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 主发布包（不含子模块内容）
        sources = self.conan_data["sources"]
        get(self, **{k: v for k, v in sources.items() if k != "submodules"},
            strip_root=True)
        # 按 v0.38.5 标签固定 commit 展开 13 个子模块。
        # 真机预检每次重跑都会重建 source 目录：conan get() 不做跨次缓存，
        # 13 个归档（aws-lc 一个就 ~145MB）串行下载把 source 阶段拉得很长，
        # 曾被外部 SIGTERM 打断在收尾处。这里改为：
        #   1) tarball 按 sha256 落盘在 conan home 的持久缓存，重跑秒级复用；
        #   2) 并行下载（每 URL 沿用 conandata.yml 的镜像有序列表逐个回退，
        #      流式 sha256 校验，内容完整性不依赖传输层信任）；
        #   3) 解压保持顺序执行，语义与 get(strip_root=True) 一致。
        subs = sources.get("submodules", [])
        if not subs:
            return
        cache_dir = self._src_cache_dir()
        results, failures = {}, []
        lock = threading.Lock()

        def _fetch(sub):
            try:
                path = self._download_to_cache(sub["url"], sub["sha256"], cache_dir)
                with lock:
                    results[sub["path"]] = path
                    self.output.info("tarball ready: %s" % sub["path"])
            except Exception as exc:  # noqa: BLE001 — 聚合后统一抛出
                with lock:
                    failures.append("%s: %s" % (sub["path"], exc))

        workers = min(4, len(subs))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_fetch, subs))
        if failures:
            raise ConanException(
                "submodule download failed -> " + "; ".join(failures))

        for sub in subs:
            dest = os.path.join(self.source_folder, sub["path"])
            os.makedirs(dest, exist_ok=True)
            self._extract_strip_root(results[sub["path"]], dest)

    # ─────────────────────── 子模块源码获取辅助 ───────────────────────

    def _src_cache_dir(self):
        """持久 tarball 缓存目录：挂在 conan home 下，跨预检重跑复用。"""
        base = getattr(self, "home_folder", None) or self.source_folder
        cache_dir = os.path.join(str(base), "hcrt_src_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    @staticmethod
    def _sha256_file(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _open_url(self, url):
        req = urllib.request.Request(
            url, headers={"User-Agent": "conan-aws-crt-recipe/0.38.5"})
        try:
            return urllib.request.urlopen(req, timeout=90)
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), ssl.SSLError):
                # 个别最小化系统无 CA bundle：降级重试；内容完整性仍由
                # sha256 强校验保证，不受传输层信任影响。
                self.output.info("TLS verify failed (%s); retrying unverified, "
                                 "content still sha256-checked" % exc.reason)
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                return urllib.request.urlopen(req, timeout=90, context=ctx)
            raise

    def _download_to_cache(self, urls, sha256, cache_dir):
        """按 conandata 有序 URL 列表逐个回退下载并流式校验 sha256，
        成功后原子落盘为 <cache>/<sha256>.tar.gz 并返回该路径。"""
        target = os.path.join(cache_dir, "%s.tar.gz" % sha256)
        if os.path.isfile(target) and self._sha256_file(target) == sha256:
            return target  # 上一次预检已下载完成，直接复用
        if isinstance(urls, str):
            urls = [urls]
        os.makedirs(cache_dir, exist_ok=True)
        # 清理上次被打断的运行遗留的分片临时文件（同 target 前缀才删，
        # 不同 sha 的并行 worker 各自前缀互不影响）
        prefix = os.path.basename(target) + ".part-"
        try:
            for entry in os.listdir(cache_dir):
                if entry.startswith(prefix):
                    try:
                        os.remove(os.path.join(cache_dir, entry))
                    except OSError:
                        pass
        except OSError:
            pass
        tmp_path = "%s.part-%d-%d" % (target, os.getpid(),
                                      threading.get_ident())
        errors = []
        try:
            for url in urls:
                try:
                    digest = hashlib.sha256()
                    resp = self._open_url(url)
                    try:
                        with open(tmp_path, "wb") as out:
                            while True:
                                chunk = resp.read(1 << 20)
                                if not chunk:
                                    break
                                digest.update(chunk)
                                out.write(chunk)
                    finally:
                        resp.close()
                    actual = digest.hexdigest()
                    if actual != sha256:
                        raise ConanException(
                            "sha256 mismatch (got %s)" % actual)
                    os.replace(tmp_path, target)
                    return target
                except Exception as exc:  # noqa: BLE001 — 记录后试下一镜像
                    errors.append("%s: %s" % (url.rsplit("/", 1)[-1], exc))
                    if os.path.isfile(tmp_path):
                        os.remove(tmp_path)
        finally:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        raise ConanException("all mirrors failed (%d tried): %s"
                             % (len(urls), "; ".join(errors)))

    @staticmethod
    def _extract_strip_root(tar_path, destination):
        """等价于 conan.tools.files.get(strip_root=True, destination=...)：
        归档须含唯一顶层目录，其内容被展开到 destination。"""
        with tarfile.open(tar_path, "r:*") as tf:
            roots = set()
            for member in tf.getmembers():
                top = member.name.split("/")[0]
                if top not in ("", ".", ".."):
                    roots.add(top)
            if len(roots) != 1:
                raise ConanException(
                    "%s: expected exactly one top-level dir, got %s"
                    % (os.path.basename(tar_path), sorted(roots)))
            root = next(iter(roots))
            tmp_dir = tempfile.mkdtemp(prefix="hcrt-x-",
                                       dir=os.path.dirname(destination))
            try:
                try:
                    tf.extractall(tmp_dir, filter="data")
                except TypeError:  # Python <3.12 无 filter 参数
                    tf.extractall(tmp_dir)
                src_root = os.path.join(tmp_dir, root)
                for entry in os.listdir(src_root):
                    shutil.move(os.path.join(src_root, entry),
                                os.path.join(destination, entry))
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            # OHOS 经 toolchain 映射为 HarmonyOS，aws-c-io 只认 Linux/Android，
            # 强制按 Linux 处理（musl/epoll 兼容）。
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            arch = str(self.settings.arch)
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if arch == "armv8" else arch
            )
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
                "ON" if self.options.get_safe("fPIC", True) else "OFF"
            )
        tc.variables["ENFORCE_SUBMODULE_VERSIONS"] = "OFF"
        # ── 上游测试套件（在 build() 内以 ctest 执行）──
        tc.variables["BUILD_TESTING"] = "ON"
        # 关闭网络用例注册：add_net_test_case 全部不进入离线发现集
        tc.variables["ENABLE_NET_TESTS"] = "OFF"
        # 代理集成测试需要本地代理服务器
        tc.variables["ENABLE_PROXY_INTEGRATION_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        result = self._run_upstream_tests()
        # 文件名必须与 test_package 硬校验的包内路径 res/upstream_test_result.json
        # 一致：package() 按原名复制，改名会让证据链断裂（曾因写成
        # ohos_upstream_test_result.json 而被 test_package 判定缺失）。
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    # ────────────────────────── 上游测试执行 ──────────────────────────

    def _locate_ctest(self):
        ctest = shutil.which("ctest")
        if ctest:
            return ctest
        cmake_path = self.conf.get("user.hmbs:cmake_path")
        if cmake_path:
            candidate = os.path.join(os.path.dirname(str(cmake_path)), "ctest")
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "ctest executable not found (PATH and user.hmbs:cmake_path both "
            "unhelpful); cannot run upstream tests"
        )

    @staticmethod
    def _parse_discovery(output):
        m = re.search(r"Total Tests:\s*(\d+)", output)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _parse_summary(output):
        """Parse 'N% tests passed, F tests failed out of T' plus not-run list."""
        failed = skipped = executed = passed = 0
        total = None
        m = re.search(r"(\d+)% tests passed,\s*(\d+) tests failed out of (\d+)",
                      output)
        if m:
            failed = int(m.group(2))
            total = int(m.group(3))
        skipped = len(re.findall(r"^\s*\d+\s+-\s+.+\((?:Not Run|Skipped)\)\s*$",
                                 output, flags=re.MULTILINE))
        if total is not None:
            executed = total - skipped
            passed = total - failed - skipped
        return executed, passed, failed, skipped

    def _run_upstream_tests(self):
        ctest = self._locate_ctest()
        bdir = self.build_folder

        discovery_cmd = [ctest, "-N", "--test-dir", bdir]
        disc = subprocess.run(discovery_cmd, capture_output=True, text=True,
                              timeout=600)
        discovered = self._parse_discovery(disc.stdout or "")

        run_cmd = [ctest, "--test-dir", bdir, "--output-on-failure",
                   "--timeout", "300"]
        try:
            proc = subprocess.run(run_cmd, capture_output=True, text=True,
                                  timeout=3600)
            output = (proc.stdout or "") + (proc.stderr or "")
            rc = proc.returncode
        except subprocess.TimeoutExpired as exc:
            output = f"ctest timed out after {exc.timeout}s"
            rc = -1

        executed, passed, failed, skipped = self._parse_summary(output or "")
        command_str = "{} && {}".format(
            " ".join(discovery_cmd), " ".join(run_cmd))

        status_ok = (
            rc == 0
            and discovered > 0
            and failed == 0
            and skipped == 0
            and executed == discovered
            and passed == discovered
        )
        result = {
            "status": "passed" if status_ok else "failed",
            "framework": "ctest",
            "command": command_str,
            "discovered": discovered,
            "executed": max(executed, 0),
            "passed": max(passed, 0),
            "failed": failed,
            "skipped": skipped,
        }
        if not status_ok:
            result["reason"] = (
                f"ctest rc={rc}; expected all {discovered} registered cases to "
                f"pass without skip; tail: ...{(output or '')[-1500:]}"
            )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            self.output.info((output or "")[-4000:])
            raise ConanException("aws-crt upstream tests did not fully pass")
        return result

    # ─────────────────────────── 打包与信息 ───────────────────────────

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # 打包上游测试证据 JSON；缺失说明 build() 未真正执行过上游测试。
        # 包内路径 res/upstream_test_result.json 是 test_package 复发
        # HMBS_UPSTREAM_TEST_RESULT 标记的唯一依据，文件名不可更改。
        result_src = os.path.join(self.build_folder, "upstream_test_result.json")
        if not os.path.isfile(result_src):
            raise ConanException(
                "upstream_test_result.json missing from build folder — "
                "upstream tests never ran; refusing to package silently"
            )
        copy(self, "upstream_test_result.json", self.build_folder,
             os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        # BUILD_DEPS=ON 模式下各 aws-c-* 静态库同样被 install()，但下游消费
        # 只需链接 aws-crt-cpp；捆绑依赖经 --whole-archive 注入，避免链接器
        # 丢弃未被直接引用的对象（错误注册表、加密后端构造等）。
        self.cpp_info.libs = ["aws-crt-cpp"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            bundled_libs = [
                "-laws-c-auth", "-laws-c-http", "-laws-c-mqtt", "-laws-c-s3",
                "-laws-c-event-stream", "-laws-checksums", "-laws-c-sdkutils",
                "-laws-c-cal", "-laws-c-io", "-laws-c-compression",
                "-laws-c-common", "-ls2n", "-lcrypto",
            ]
            whole = ["-Wl,--whole-archive"] + bundled_libs + ["-Wl,--no-whole-archive"]
            self.cpp_info.exelinkflags = whole
            self.cpp_info.sharedlinkflags = whole
            self.cpp_info.system_libs = ["pthread", "dl", "rt", "m"]
