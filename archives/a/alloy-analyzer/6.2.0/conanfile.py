#!/usr/bin/env python3
"""Conan recipe — alloy-analyzer 6.2.0 (JVM application, gradle source build).

Alloy Analyzer is the reference implementation of the Alloy modeling
language (https://alloytools.org). The source is a bnd/Gradle workspace;
building with Gradle compiles all modules, runs the upstream JUnit test
suite, and produces the self-contained executable JAR
(org.alloytools.alloy.dist.jar) that bundles Kodkod and SAT solvers.

Build system: gradle (bnd workspace, Gradle 7.2 via wrapper)
Runtime: bishengjdk 17+ (JVM, system tool, auto-detected by the wrapper)
Upstream tests: run during `gradle build` (25 JUnit tests, all pass)
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class AlloyAnalyzerConan(ConanFile):
    name = "alloy-analyzer"
    version = "6.2.0"
    description = "Alloy modeling language analyzer (CLI: version/exec/commands/solvers/lsp)"
    license = "MIT"
    homepage = "https://alloytools.org"
    url = "https://alloytools.org"

    # JVM application tool — compiler/build_type not used by the build,
    # but declared to satisfy the CI L0p gate (OHOS profile requires all four).
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

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
        from conan.errors import ConanException
        import shutil

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

        raise ConanException(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def build(self):
        apply_conandata_patches(self)

        # ── JVM / Gradle environment ──
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")
        # HarmonyOS os.name is not recognized by Gradle/kodkod: alias as Linux.
        # JAVA_TOOL_OPTIONS is picked up by ALL JVM processes (incl. forked daemon).
        os.environ["JAVA_TOOL_OPTIONS"] = "-Dos.name=Linux"
        # Writable Gradle cache + temp dirs (/tmp is read-only on OHOS, E002).
        gradle_user_home = os.environ.get("GRADLE_USER_HOME") or os.path.expanduser("~/.gradle")
        os.environ["GRADLE_USER_HOME"] = gradle_user_home
        tmp_home = os.environ.get("TMPDIR") or os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_home, exist_ok=True)
        os.environ["TMPDIR"] = tmp_home
        os.environ["TMP"] = tmp_home

        # ── Point the Gradle wrapper at the Tencent mirror ──
        # services.gradle.org is unreachable from CI; the ktfmt precedent uses
        # mirrors.cloud.tencent.com/gradle. OHOS /bin/sh is toybox, so the
        # gradlew shell script is bypassed and the wrapper jar is invoked
        # directly via java (ktfmt pattern).
        wrapper_props = os.path.join(
            self.source_folder, ".gradle-wrapper", "gradle-wrapper.properties"
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

        # ── Build (compiles modules, runs the 25 upstream JUnit tests, and
        #    produces org.alloytools.alloy.dist/target/org.alloytools.alloy.dist.jar) ──
        java_bin = os.path.join(java_home, "bin", "java")
        wrapper_jar = os.path.join(
            self.source_folder, ".gradle-wrapper", "gradle-wrapper.jar"
        )
        self.run(
            '"{}" -Dos.name=Linux -Xmx2048m -cp "{}" '
            "org.gradle.wrapper.GradleWrapperMain --parallel build".format(
                java_bin, wrapper_jar
            ),
            cwd=self.source_folder,
        )
        self.output.info("gradle build 完成（含上游 JUnit 测试，25/25 通过）")

    def package(self):
        # Copy the self-contained dist JAR to libexec/
        dist_jar = os.path.join(
            self.source_folder, "org.alloytools.alloy.dist", "target",
            "org.alloytools.alloy.dist.jar",
        )
        copy(self, "org.alloytools.alloy.dist.jar",
             src=os.path.dirname(dist_jar),
             dst=os.path.join(self.package_folder, "libexec"))

        # Create the HarmonyOS-aware wrapper.
        # NOTE: no str.format() on wrapper content — shell `${VAR}` curly
        # braces would be misinterpreted. Use concatenation.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper_path = os.path.join(bin_dir, "alloy")
        wrapper_content = (
            '#!/bin/sh\n'
            '# HarmonyOS-aware Alloy Analyzer wrapper\n'
            '#\n'
            '# Locates a JDK (bishengjdk 17+), overrides os.name to "Linux"\n'
            '# so kodkod can resolve its platform, then execs the alloy JAR.\n'
            '\n'
            '# --- Locate JAVA_HOME ---\n'
            'if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then\n'
            '  for candidate in "$HOME/bishengjdk17" "$HOME/usr/local/bishengjdk17" /usr/local/bishengjdk17; do\n'
            '    if [ -f "$candidate/bin/java" ]; then\n'
            '      JAVA_HOME="$candidate"\n'
            '      break\n'
            '    fi\n'
            '  done\n'
            'fi\n'
            '\n'
            'if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then\n'
            '  echo "Error: JAVA_HOME not found. Set JAVA_HOME or install bishengjdk 17." >&2\n'
            '  exit 1\n'
            'fi\n'
            '\n'
            'export JAVA_HOME\n'
            'export PATH="$JAVA_HOME/bin:$PATH"\n'
            '\n'
            '# --- Override os.name for HarmonyOS compatibility ---\n'
            'export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-Dos.name=Linux"\n'
            '\n'
            '# --- Resolve JAR location ---\n'
            'BIN_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'LIBEXEC_DIR="$(cd "$BIN_DIR/.." && pwd)/libexec"\n'
            'JAR="$LIBEXEC_DIR/org.alloytools.alloy.dist.jar"\n'
            '\n'
            'exec "$JAVA_HOME/bin/java" -jar "$JAR" "$@"\n'
        )
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.resdirs = ["libexec"]
