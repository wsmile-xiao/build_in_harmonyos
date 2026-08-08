#!/usr/bin/env python3
"""Conan recipe — xom 1.4.4 (Ant + Ivy, JUnit).

XOM (XML Object Model) is a Java library (LGPL-2.1+) built with
Ant + Ivy. The upstream test target is `ant test`, which runs a
JUnit 4 batchtest over src/nu/xom/tests/*Test.java (42 files; the
build.xml test target excludes MegaTest.java and EBCDICTest.java,
so 40 test classes are executed).

Build toolchain: bishengjdk 17 + Apache Ant 1.10.x (system tools
on the HarmonyOS PC real machine). Ivy resolves the runtime and
test dependencies (Xerces 2.12.2, xml-apis 1.4.01, Jaxen 2.0.3
whose source zip ships in the repo, JUnit 4.13.2, tagsoup 1.2.1,
saxon 6.5.3, servlet-api 2.5, jarjar 1.3, clover 4.5.2).

R32: settings.os check uses `in ("Linux", "OHOS")`.
R28: test_package/ included.
R34: the consumer test compiles and runs a Java program that
exercises the packaged XOM API.
"""

import glob
import json
import os
import shutil
import stat
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class XomConan(ConanFile):
    name = "xom"
    version = "1.4.4"
    description = "XOM — a tree-based Java API for processing XML with correctness, simplicity, and performance"
    license = "LGPL-2.1-or-later"
    homepage = "https://xom.nu/"
    url = "https://github.com/elharo/xom"

    package_type = "library"
    settings = "os", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OS compatibility check — must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xom is a JVM library packaged for Linux/OpenHarmony"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _java_executable(java_home, tool):
        suffix = ".exe" if os.name == "nt" else ""
        return os.path.join(java_home, "bin", tool + suffix)

    def _resolve_java(self):
        """Locate a usable bishengjdk 17 (or compatible) JAVA_HOME.

        Order: JAVA_HOME env → common install locations (incl. real-machine
        ~/bishengjdk17 and cmd-pkgs flat dst ~/usr/local) → java on PATH →
        cmd-pkgs download via conan get() (mirrors _resolve_ant's fallback,
        avoids curl which is absent on CI worker). Raises ConanException
        when no JDK can be found after all fallbacks.
        """
        env_home = os.environ.get("JAVA_HOME", "")
        if env_home and os.path.isfile(self._java_executable(env_home, "java")):
            return env_home

        for candidate in (
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/storage/Users/currentUser/bishengjdk17",
            "/storage/Users/currentUser/usr/local",
            "/usr/local/bishengjdk17",
            "/usr/local",
        ):
            if os.path.isfile(self._java_executable(candidate, "java")):
                return candidate

        java_on_path = shutil.which("java")
        if java_on_path:
            return os.path.dirname(os.path.dirname(os.path.realpath(java_on_path)))

        # R18: 主动通过 cmd-pkgs 下载 bishengjdk 17.0.13（对齐 _resolve_ant 模式，
        # 不依赖 curl —— CI worker 未安装 curl）
        jdk_version = "17.0.13"
        jdk_dir = os.path.join(self.build_folder, "bishengjdk17")
        if not os.path.isfile(self._java_executable(jdk_dir, "java")):
            jdk_url = (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                "download/pkgs/bishengjdk-{}-ohos-aarch64.tar.gz".format(jdk_version)
            )
            # cmd-pkgs tar.gz 解压后顶层可能是 flat 结构（bin/lib/share 在
            # jdk_dir 根）或带一层版本目录（jdk_dir/bishengjdk-17.0.13/bin/…）。
            # 不用 strip_root —— Conan 2 的 get() 对含顶层目录的 tar.gz
            # strip_root 行为依版本而异；改为解压后扫描 jdk_dir（含自身）找
            # 第一个含 bin/java 的目录，兼容两种布局。
            os.makedirs(jdk_dir, exist_ok=True)
            get(self, url=jdk_url, destination=jdk_dir)

            resolved = self._find_java_root(jdk_dir)
            if resolved is None:
                raise ConanException(
                    "Could not find a JDK for xom. Downloaded bishengjdk {} "
                    "via cmd-pkgs but bin/java is missing under {}. Set JAVA_HOME "
                    "or verify the cmd-pkgs bishengjdk package layout."
                    .format(jdk_version, jdk_dir)
                )
            jdk_dir = resolved

        return jdk_dir

    @staticmethod
    def _find_java_root(base_dir):
        """Scan ``base_dir`` for a directory containing ``bin/java``.

        cmd-pkgs bishengjdk archives may extract flat (``base_dir/bin/java``)
        or nested (``base_dir/<jdk-topdir>/bin/java``). We check ``base_dir``
        first, then any single-level subdirectory, returning the first match.
        Returns ``None`` when no layout yields ``bin/java``.
        """
        candidates = [base_dir]
        try:
            for entry in sorted(os.listdir(base_dir)):
                full = os.path.join(base_dir, entry)
                if os.path.isdir(full):
                    candidates.append(full)
        except OSError:
            pass
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                return candidate
        return None

    def _resolve_ant(self, java_home):
        """Locate the Apache Ant executable, preferring the system Ant.

        Falls back to ``ant`` on PATH. Returns the command (path or
        bare name) to invoke.
        """
        for candidate in (
            os.path.expanduser("~/usr/local/bin/ant"),
            "/usr/local/bin/ant",
            os.path.expanduser("~/apache-ant-1.10.15/bin/ant"),
        ):
            if os.path.isfile(candidate):
                return candidate

        ant_on_path = shutil.which("ant")
        if ant_on_path:
            return ant_on_path

        # Last resort: download Apache Ant from the official archive.
        # Conan 2's ``get()`` downloads *and* auto-extracts .tar.gz into
        # ``destination`` (deleting the archive afterwards), so we only
        # need to point it at ``build_folder`` — the extracted dir
        # ``apache-ant-X.Y.Z`` lands exactly where ``ant_home`` expects.
        ant_version = "1.10.15"
        ant_archive = "apache-ant-{}-bin.tar.gz".format(ant_version)
        ant_url = (
            "https://archive.apache.org/dist/ant/binaries/" + ant_archive
        )
        ant_home = os.path.join(self.build_folder, "apache-ant-" + ant_version)
        if not os.path.isdir(ant_home):
            get(self, url=ant_url, destination=self.build_folder)
            if not os.path.isdir(ant_home):
                raise ConanException(
                    "Downloaded Ant {} but expected dir {} is missing"
                    .format(ant_version, ant_home)
                )
        os.environ["ANT_HOME"] = ant_home
        return os.path.join(ant_home, "bin", "ant")

    @staticmethod
    def _find_built_jars(src_folder, jar_glob):
        """Locate the JAR(s) produced by ``ant jar``.

        ``ant jar`` writes ``${build.dir}/${name}-${version}.jar`` and
        also copies it into ``${dist.dir}`` (build.xml line 408). With
        the upstream defaults ``build.dir=./build`` and
        ``dist.dir=./dist`` (relative to ant's cwd = ``src_folder``)
        the candidates are::

            <src>/build/xom-1.4.4.jar   (primary)
            <src>/dist/xom-1.4.4.jar    (dist copy)
            <src>/xom-1.4.4.jar         (fallback)

        Searching all three keeps ``package()`` robust regardless of
        how Conan 2 lays out ``self.source_folder`` between build and
        package stages.
        """
        candidates = (
            os.path.join(src_folder, "build", jar_glob),
            os.path.join(src_folder, "dist", jar_glob),
            os.path.join(src_folder, jar_glob),
        )
        found = []
        for pattern in candidates:
            found.extend(glob.glob(pattern))
        # de-dup while preserving order
        seen = set()
        unique = []
        for jar in found:
            rp = os.path.realpath(jar)
            if rp not in seen:
                seen.add(rp)
                unique.append(jar)
        return unique

    @staticmethod
    def _copy_one_file(src_file, dst_dir):
        """Copy a single file into ``dst_dir``.

        Conan 2's ``tools.files.copy`` takes a *folder* as ``src`` and
        an fnmatch *pattern* — passing a file path as ``src`` makes the
        copy silently no-op (the trailing ``/`` Conan appends turns the
        file path into a non-existent directory). For staging individual
        JARs we therefore use ``shutil.copy2`` directly, which also
        preserves the upstream ``modificationtime`` that ``ant jar``
        stamps via ``<jarjar modificationtime="...">``.
        """
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src_file, os.path.join(dst_dir, os.path.basename(src_file)))

    def build(self):
        apply_conandata_patches(self)

        java_home = self._resolve_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            os.path.join(java_home, "bin")
            + os.pathsep
            + os.environ.get("PATH", "")
        )

        ant_cmd = self._resolve_ant(java_home)

        # Build the xom JAR (jar target depends on compile).
        self.run('"{}" jar'.format(ant_cmd), cwd=self.source_folder)

        # Stage the built JAR(s) and the Ivy-resolved runtime
        # dependency JARs into ``self.build_folder`` so ``package()``
        # has a single, layout-independent location to read from.
        stage = self.build_folder
        os.makedirs(stage, exist_ok=True)

        jar_glob = "xom-{}.jar".format(self.version)
        built_jars = self._find_built_jars(self.source_folder, jar_glob)
        if not built_jars:
            raise ConanException(
                "xom build did not produce the expected {} JAR "
                "(source_folder={})".format(jar_glob, self.source_folder)
            )
        for jar in built_jars:
            self._copy_one_file(jar, stage)

        # Minimal variant (optional `minimal` target output).
        minimal_glob = "xom-{}-minimal.jar".format(self.version)
        for jar in self._find_built_jars(self.source_folder, minimal_glob):
            self._copy_one_file(jar, stage)

        # Ivy-resolved runtime dependency JARs live in <src>/ivy/.
        ivy_lib = os.path.join(self.source_folder, "ivy")
        if os.path.isdir(ivy_lib):
            for dep_jar in glob.glob(os.path.join(ivy_lib, "*.jar")):
                self._copy_one_file(dep_jar, stage)

    def package(self):
        # Built artifacts are staged in ``self.build_folder`` by
        # ``build()`` (the primary xom JAR plus the Ivy-resolved
        # runtime dependency JARs). Conan 2's ``copy()`` takes a
        # *folder* as ``src`` and an fnmatch *pattern*, so we point it
        # at the staging folder with the ``*.jar`` pattern — the
        # correct usage that the previous ``copy(self, basename, file,
        # dir)`` form violated, causing a silent no-op and an empty
        # ``libexec/``.
        stage = self.build_folder
        staged_jars = glob.glob(os.path.join(stage, "*.jar"))
        if not staged_jars:
            raise ConanException(
                "xom build did not stage any JARs in {} "
                "(build_folder={})".format(stage, self.build_folder)
            )

        libexec = os.path.join(self.package_folder, "libexec")
        copy(self, "*.jar", stage, libexec)

    def package_info(self):
        # JVM library: classpath lives in libexec, no native link flags.
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.resdirs = ["libexec"]
