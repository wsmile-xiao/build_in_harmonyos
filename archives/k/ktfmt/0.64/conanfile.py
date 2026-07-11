#!/usr/bin/env python3
"""Conan recipe — ktfmt 0.64 (JVM application, gradle build).

ktfmt is a Kotlin code formatter by Facebook. It is a JVM application
built with Gradle's shadowJar task, producing a fat JAR containing all
dependencies. The packaged result is a JAR file plus a shell wrapper
script that invokes `java -jar`.

Build system: gradle (system tool or gradlew wrapper)
Runtime: bishengjdk 17 (JVM, system tool)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KtfmtConan(ConanFile):
    name = "ktfmt"
    version = "0.64"
    description = "Kotlin code formatter by Facebook"
    license = "Apache-2.0"
    homepage = "https://facebook.github.io/ktfmt/"
    url = ""  # CI fills this

    # JVM application — no compiler/build_type needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gradle and bishengjdk are system tools, not Conan-managed packages.
        # build() finds gradle at ~/usr/local/bin or falls back to gradlew.
        # bishengjdk is found via _ensure_java() (checks env, common paths,
        # or auto-installs via cmd-pkgs install-jdk.sh).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.

        Checks (in order):
          1. JAVA_HOME environment variable
          2. ~/bishengjdk17 and ~/usr/local/bishengjdk17 (standard cmd-pkgs paths)
          3. java on PATH
          4. Auto-install via cmd-pkgs install-jdk.sh (CI workers may lack JDK)

        Returns the JAVA_HOME path. Raises ConanException if all attempts fail.
        """
        # 1. Check JAVA_HOME env
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        # 2. Check common cmd-pkgs install locations
        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        # 3. Try to find java in PATH
        java_in_path = shutil.which("java")
        if java_in_path:
            # Derive JAVA_HOME from java binary path (…/bin/java → …)
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

        # 4. Auto-install bishengjdk 17.0.13 via cmd-pkgs
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

        raise ConanException(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def build(self):
        # Apply patches (none for ktfmt, but required by G1 gate)
        apply_conandata_patches(self)

        # Ensure bishengjdk 17 is available (CI workers may not have it)
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        # Prepend java bin to PATH so gradle-wrapper.jar and child processes
        # can find java without relying on .zshrc (not sourced in CI).
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")
        os.environ["GRADLE_OPTS"] = "-Xmx512m -Dos.name=Linux"
        # Gradle --no-daemon still forks a "single-use Daemon process" whose
        # JVM reads os.name from the actual system (HarmonyOS), causing
        # ExceptionInInitializerError. JAVA_TOOL_OPTIONS is picked up by ALL
        # JVM processes including the forked daemon, overriding os.name.
        os.environ["JAVA_TOOL_OPTIONS"] = "-Dos.name=Linux"
        # GRADLE_USER_HOME: use ~/.gradle (writable, persists wrapper dist cache)
        gradle_user_home = os.environ.get("GRADLE_USER_HOME") or os.path.expanduser("~/.gradle")
        os.environ["GRADLE_USER_HOME"] = gradle_user_home

        # Gradle's OperatingSystem class doesn't recognize "HarmonyOS" and
        # throws ExceptionInInitializerError during static init. OHOS is
        # Linux-based at the kernel level, so alias as Linux.
        # gradle.properties sets org.gradle.jvmargs for the daemon JVM
        # (the launcher gets -Dos.name=Linux via the java command line).
        gradle_props = os.path.join(self.source_folder, "gradle.properties")
        with open(gradle_props, "a") as f:
            f.write("\norg.gradle.jvmargs=-Xmx512m -Dos.name=Linux\n")

        # Find gradle: check system locations first, fall back to gradlew
        gradle_cmd = None
        for candidate in [
            os.path.expanduser("~/usr/local/bin/gradle"),
            "/usr/local/bin/gradle",
        ]:
            if os.path.isfile(candidate):
                gradle_cmd = candidate
                break

        if gradle_cmd:
            self.run(
                '"{}" shadowJar --no-daemon -Dorg.gradle.daemon=false'.format(
                    gradle_cmd
                ),
                cwd=self.source_folder,
            )
        else:
            # Use gradle wrapper JAR directly (gradlew script needs POSIX sh,
            # but OHOS /bin/sh is toybox which lacks required features).
            # Replace distribution URL with Tencent mirror (faster in China).
            wrapper_props = os.path.join(
                self.source_folder, "gradle", "wrapper",
                "gradle-wrapper.properties",
            )
            if os.path.isfile(wrapper_props):
                with open(wrapper_props, "r") as f:
                    content = f.read()
                content = content.replace(
                    "services.gradle.org/distributions",
                    "mirrors.cloud.tencent.com/gradle",
                )
                with open(wrapper_props, "w") as f:
                    f.write(content)
            # Invoke gradle-wrapper.jar via java directly
            java_bin = os.path.join(java_home, "bin", "java")
            wrapper_jar = os.path.join(
                self.source_folder, "gradle", "wrapper", "gradle-wrapper.jar"
            )
            self.run(
                '"{}" -Dos.name=Linux -cp "{}" org.gradle.wrapper.GradleWrapperMain'
                " shadowJar --no-daemon -Dorg.gradle.daemon=false".format(
                    java_bin, wrapper_jar
                ),
                cwd=self.source_folder,
            )

    def package(self):
        # Copy the fat JAR to libexec/
        copy(
            self,
            "ktfmt-{}-with-dependencies.jar".format(self.version),
            src=os.path.join(self.source_folder, "core", "build", "libs"),
            dst=os.path.join(self.package_folder, "libexec"),
        )

        # Create wrapper script
        # NOTE: Do NOT use .format() on the wrapper content — the shell
        # variables ${JAVA_HOME} etc. contain curly braces that Python's
        # str.format() would misinterpret as placeholders. Use concatenation.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper_path = os.path.join(bin_dir, "ktfmt")
        wrapper_content = (
            "#!/bin/sh\n"
            'export JAVA_HOME="${JAVA_HOME:-$HOME/bishengjdk17}"\n'
            'export PATH="$JAVA_HOME/bin:$PATH"\n'
            'JAR_DIR="$(cd "$(dirname "$0")/.." && pwd)/libexec"\n'
            'exec java -jar "$JAR_DIR/ktfmt-'
            + self.version
            + '-with-dependencies.jar" "$@"\n'
        )
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        # Define bindirs for the wrapper script and resdirs for the JAR
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.resdirs = ["libexec"]
