#!/usr/bin/env python3
"""Conan recipe — keycloak-archlinux 2.0.1 (Arch Linux Keycloak theme JAR).

Upstream: https://gitlab.archlinux.org/archlinux/keycloak-archlinux-theme
(tag v2.0.1, v-prefix). Task-card name `keycloak-archlinux` maps to the Arch
package `keycloak-archlinux-theme 2.0.1-1` (extra, arch=any) — the upstream
project IS the Arch Linux GitLab project.

The upstream repo carries two build paths:
  * v2/    keycloakify toolchain (React 18 + Vite + yarn + Maven) — the path
           Arch's PKGBUILD packages;
  * root/  classic Gradle build (pure FTL/CSS/image theme resources) —
           documented by the upstream README and built by upstream CI
           (.gitlab-ci.yml `build` job -> lib/build/libs/keycloak-archlinux-theme.jar).

This recipe uses the GRADLE path, which is one of the two upstream-supported
builds. The keycloakify path cannot run on OHOS devices: Vite hard-requires
esbuild, a foreign prebuilt Go binary, and the HarmonyOS
SecureAccessFence refuses exec() for any ELF that does not carry the
.note.ohos.ident section emitted by the OHOS toolchain (verified empirically:
locally built binaries run; renaming the section, zeroing the note or
stripping the section table each flip exec to EPERM/ENOEXEC-class denials).
The Gradle path needs only a JDK — no Node/yarn/esbuild/Maven at all — and
produces the upstream-supported classic theme JAR. The deviation is recorded
in notes.md and manifest.yaml.

Package layout (follows archives/k/keycloak-metrics/7.0.0 precedent):
  lib/keycloak-archlinux-theme.jar   <- theme resource JAR
  licenses/LICENSE

Build chain:
  bishengjdk 17.0.13 (auto-install via cmd-pkgs, same as keycloak-metrics)
  + Gradle 9.3.0 (mirror pre-fetch, wrapper pointed at the local zip,
    invoked via GradleWrapperMain — same chain as keycloak-metrics 7.0.0)

Upstream has NO test suite (PKGBUILD has no check(); .gitlab-ci.yml only has
build jobs; neither build path ships tests). Consumer verification happens in
test_package via JAR structure assertions + a JVM resource-loading probe
(NO_UPSTREAM_TESTS, see test_package/MANIFEST.yml).

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package performs real consumer-side verification
R38: library package (theme JAR, no executables) — no commands.json
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy


class KeycloakArchlinuxThemeConan(ConanFile):
    name = "keycloak-archlinux"
    version = "2.0.1"
    description = (
        "Arch Linux theme for the Keycloak IAM server "
        "(login/account/admin/email/welcome FTL theme packaged as a "
        "Keycloak provider JAR)"
    )
    license = "Apache-2.0"
    homepage = "https://gitlab.archlinux.org/archlinux/keycloak-archlinux-theme"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    # Gradle 发行版：官方 services.gradle.org 在 CI worker 上直连常超时，
    # 使用腾讯云镜像预下载后把 wrapper distributionUrl 指向本地文件
    # （keycloak-metrics 7.0.0 同款方案）。
    _gradle_version = "9.3.0"
    _gradle_zip_url = (
        "https://mirrors.cloud.tencent.com/gradle/gradle-9.3.0-bin.zip"
    )
    # 腾讯镜像 gradle-9.3.0-bin.zip 的固定 sha256（免证书下载通道的完整性兜底）
    _gradle_zip_sha256 = (
        "0d585f69da091fc5b2beced877feab55a3064d43b8a1d46aeb07996b0915e0e0"
    )

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"keycloak-archlinux does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.

        Same chain as archives/k/keycloak-metrics/7.0.0:
          1. JAVA_HOME environment variable
          2. ~/bishengjdk17 (standard cmd-pkgs path)
          3. java on PATH
          4. Auto-install via cmd-pkgs install-jdk.sh
        """
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

        self.output.info("Java not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh"
        )
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))

        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home

        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def _prepare_gradle(self):
        """Fetch the Gradle distribution via mirror and point the wrapper at it.

        上游 gradlew 脚本在本机会因 HMDFS 禁 shebang exec / busybox xargs
        引号问题而无法直接执行（keycloak-metrics 7.0.0 同坑）；wrapper 默认
        从 services.gradle.org 下载，直连超时。因此：
          1. curl / python3 urllib 从腾讯镜像预下载 gradle 发行版 zip
             （sha256 钉校验兜底完整性）
          2. 改 gradle-wrapper.properties 的 distributionUrl 为 file:// 本地路径
             （properties 后写的同名 key 生效，不动原始行）
          3. 绕过 gradlew 脚本，直接 java -cp gradle-wrapper.jar 调
             GradleWrapperMain（wrapper 只负责解压/定位发行版，语义不变）
        """
        wrapper_props = os.path.join(
            self.source_folder, "gradle", "wrapper", "gradle-wrapper.properties"
        )
        zip_path = os.path.join(self.build_folder, "gradle-9.3.0-bin.zip")

        def _sha256(path):
            import hashlib
            h = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            return h.hexdigest()

        if not os.path.isfile(zip_path) or _sha256(zip_path) != self._gradle_zip_sha256:
            if os.path.isfile(zip_path):
                os.remove(zip_path)
            self.output.info("Downloading Gradle 9.3.0 from mirror ...")
            # 先走 curl（conanbuild 环境若提供系统 curl 则最稳），
            # 失败再退回 python3 urllib 免证书下载 + sha256 钉校验
            # （设备可能无 CA bundle，见 knowledge DRAFT-12609 双通道方案）。
            dl_py = (
                "import ssl,urllib.request,shutil;"
                "ctx=ssl._create_unverified_context();"
                "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                "r=o.open('{}',timeout=900);f=open('{}','wb');"
                "shutil.copyfileobj(r,f);f.close();r.close()"
            ).format(self._gradle_zip_url, zip_path)
            try:
                self.run('curl -fsSL --retry 3 --max-time 900 -o "{}" "{}"'.format(
                    zip_path, self._gradle_zip_url))
            except Exception:
                self.output.info("curl unavailable/failed — python3 urllib fallback")
                self.run('python3 -c "{}"'.format(dl_py))

            got = _sha256(zip_path)
            if got != self._gradle_zip_sha256:
                raise ConanInvalidConfiguration(
                    "Gradle distribution sha256 mismatch: got {}, expected {}".format(
                        got, self._gradle_zip_sha256))

        # wrapper distributionUrl -> 本地 zip（file 协议）。
        # properties 文件后写的同名 key 生效（java.util.Properties 语义），
        # 与 keycloak-metrics 相同的追加式改写。
        with open(wrapper_props, "a", encoding="utf-8") as f:
            f.write(
                "\n# PATCHED by conanfile: use pre-fetched local distribution\n"
                f"distributionUrl=file\\://{zip_path}\n"
            )
        self.output.info(f"wrapper distributionUrl -> file://{zip_path}")

    def _gradle(self, *tasks):
        """Invoke the gradle wrapper without the gradlew shell script."""
        wrapper_jar = os.path.join(
            self.source_folder, "gradle", "wrapper", "gradle-wrapper.jar"
        )
        task_args = " ".join(tasks)
        self.run(
            f'java -Dorg.gradle.appname=gradlew -classpath "{wrapper_jar}" '
            f"org.gradle.wrapper.GradleWrapperMain {task_args} --no-daemon",
            env="conanbuild",
        )

    def build(self):
        # 1) JDK 17（CI worker 可能未预装，自动通过 cmd-pkgs 安装）
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + os.pathsep + os.environ.get("PATH", "")

        # 本机 bishengjdk17 的 libjvm.so 依赖 libc++_shared.so（鸿蒙平台），
        # conan 缓存中若有 clang/libcxx 包则加入 LD_LIBRARY_PATH
        # （keycloak-metrics 同款兜底；本包纯资源构建通常用不到）。
        # 通用化：按包名前缀匹配本地 conan 缓存，不针对特定 revision。
        conan_libcxx_dirs = sorted(
            glob.glob(os.path.expanduser("~/.conan2/p/clang*/p/lib"))
        )
        for conan_libcxx in conan_libcxx_dirs:
            if os.path.isdir(conan_libcxx):
                os.environ["LD_LIBRARY_PATH"] = (
                    conan_libcxx + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
                )
                self.output.info(
                    "Added conan clang libc lib dir to LD_LIBRARY_PATH: "
                    + conan_libcxx
                )
                break

        # 2) Gradle 9.3.0 发行版（镜像预下载 + wrapper 指向本地）
        self._prepare_gradle()

        # 3) 构建：与上游 CI（.gitlab-ci.yml build job 的 `gradle build`）一致。
        #    产物：lib/build/libs/keycloak-archlinux-theme.jar（纯资源主题 JAR，
        #    无 Java 源码；build 含 assemble+check，check 的 test 子任务无测试源
        #    时按 NO-SOURCE 跳过——上游本就无测试套件）。
        self._gradle("build")

    def package(self):
        jar_path = os.path.join(
            self.source_folder, "lib", "build", "libs",
            "keycloak-archlinux-theme.jar"
        )
        if not os.path.exists(jar_path):
            raise ConanInvalidConfiguration(
                f"Build artifact not found: {jar_path}. "
                "Ensure the Gradle build completed successfully."
            )
        copy(
            self,
            "keycloak-archlinux-theme.jar",
            os.path.join(self.source_folder, "lib", "build", "libs"),
            os.path.join(self.package_folder, "lib"),
        )
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
