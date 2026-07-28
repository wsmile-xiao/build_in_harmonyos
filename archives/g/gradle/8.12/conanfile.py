#!/usr/bin/env python3
"""Conan recipe — gradle 8.12 (JVM application, binary distribution).

Gradle is a build automation tool for multi-language software development.
It is a JVM application distributed as a binary ZIP containing shell scripts
and JAR files. The packaged result is the standard Gradle distribution with
a HarmonyOS-compatible wrapper script.

Build system: binary distribution (pre-built)
Runtime: bishengjdk 17+ (JVM, system tool)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class GradleConan(ConanFile):
    name = "gradle"
    version = "8.12"
    description = "Adaptable, fast automation for all"
    license = "Apache-2.0"
    homepage = "https://gradle.org"

    # JVM application — no compiler/build_type needed
    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No compilation needed — binary distribution is pre-built.
        pass

    def package(self):
        # Copy the entire distribution into the package
        copy(self, "*",
             src=self.source_folder,
             dst=self.package_folder)

        # Overwrite bin/gradle with a HarmonyOS-aware wrapper
        self._create_wrapper()

        # No upstream test marker is emitted here or in test_package.
        # Gradle is a JVM precompiled distribution: the binary zip carries
        # no build-system test harness (no configure/make/make check, no
        # CTest entry, no test sources). Same pattern as scala/avro-tools/
        # ktfmt in this archive. The consumer-side smoke test in
        # test_package/test.sh emits HMBS_TEST_PACKAGE_RESULT. PR body
        # ## 补充说明 notes the distribution shape.

    def _create_wrapper(self):
        """Create a HarmonyOS-aware gradle wrapper script.

        Handles:
        1. Finding JAVA_HOME (bishengjdk or user-set)
        2. Overriding os.name to "Linux" (Gradle's OperatingSystem
           class doesn't recognize "HarmonyOS" and throws
           ExceptionInInitializerError)
        """
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper_path = os.path.join(bin_dir, "gradle")

        wrapper_content = (
            '#!/bin/sh\n'
            '# HarmonyOS-aware Gradle wrapper\n'
            '#\n'
            '# Finds JAVA_HOME and overrides os.name so Gradle\'s\n'
            '# OperatingSystem class works on HarmonyOS.\n'
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
            '# Gradle\'s OperatingSystem class does not recognize "HarmonyOS"\n'
            '# and throws ExceptionInInitializerError. JAVA_TOOL_OPTIONS is\n'
            '# picked up by ALL JVM processes including the forked daemon.\n'
            '# Always append -Dos.name=Linux so it works even when\n'
            '# JAVA_TOOL_OPTIONS is already set (e.g. -Xmx512m).\n'
            'export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-Dos.name=Linux"\n'
            '\n'
            '# --- Resolve the real gradle script location ---\n'
            'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'GRADLE_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"\n'
            'export GRADLE_HOME\n'
            '\n'
            '# --- Execute the real Gradle launcher ---\n'
            '# Build the classpath from all JARs in lib/\n'
            'CLASSPATH=""\n'
            'shopt -s nullglob\n'
            'for jar in "$GRADLE_HOME/lib/"*.jar; do\n'
            '  if [ -z "$CLASSPATH" ]; then\n'
            '    CLASSPATH="$jar"\n'
            '  else\n'
            '    CLASSPATH="$CLASSPATH:$jar"\n'
            '  fi\n'
            'done\n'
            'shopt -u nullglob\n'
            '\n'
            'exec "$JAVA_HOME/bin/java" \\\n'
            '  -Dorg.gradle.appname=gradle \\\n'
            '  -classpath "$CLASSPATH" \\\n'
            '  org.gradle.launcher.GradleMain \\\n'
            '  "$@"\n'
        )
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        import json
        result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (JVM precompiled distribution)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Gradle is a JVM precompiled distribution; no C/C++ build-system test suite"
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(result)}")
        # Define bindirs for the wrapper script
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]