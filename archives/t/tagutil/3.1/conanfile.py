#!/usr/bin/env python3
"""Conan recipe for tagutil 3.1."""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class TagutilConan(ConanFile):
    name = "tagutil"
    version = "3.1"
    description = "Command-line editor for audio file tags"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kAworu/tagutil"
    url = "https://github.com/kAworu/tagutil"
    package_type = "application"
    expected_upstream_scenarios = 51

    settings = "os", "compiler", "build_type", "arch"
    default_options = {
        "libyaml/*:shared": False,
        "jansson/*:shared": False,
        "taglib/*:shared": False,
        "flac/*:shared": False,
        "libogg/*:shared": False,
        "libvorbis/*:shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # rspec 3.9.0 is two Ruby source files. The other Cucumber
        # dependencies are downloaded from codeload tags in build().
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "vendor-ruby"),
             dst=os.path.join(self.export_sources_folder, "vendor-ruby"))

    def requirements(self):
        self.requires("libyaml/0.2.5")
        self.requires("jansson/2.14")
        self.requires("taglib/1.13.1")
        self.requires("flac/1.4.3")
        # Both registry FLAC and Vorbis recipes pin different compatible Ogg
        # patch releases. Keep one Conan node for their shared ABI dependency.
        self.requires("libogg/1.3.6", override=True)
        self.requires("libvorbis/1.3.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Codeload URLs end in the tag name. Without an explicit filename,
        # Conan treats the payload as a zip and raises BadZipFile.
        get(self, filename="tagutil-3.1.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_RUNTIME_OUTPUT_DIRECTORY"] = os.path.join(
            self.build_folder, "runtime")
        tc.generate()
        PkgConfigDeps(self).generate()
        # Upstream FindPkgConfig asks for yaml-0.1; the registry package name
        # produces libyaml.pc, so provide the standard upstream module alias.
        yaml_pc = os.path.join(self.generators_folder, "libyaml.pc")
        if os.path.isfile(yaml_pc):
            shutil.copy2(yaml_pc, os.path.join(self.generators_folder, "yaml-0.1.pc"))

    def _signing_tools(self):
        # CI workers keep the HNP copies at a fixed path. A developer device
        # may only have the same tools on PATH (harmonybrew ohos-sdk) and
        # cannot create /data/service/hnp. Prefer the HNP paths so CI behavior
        # stays on those binaries.
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if os.path.isfile(objcopy) and os.path.isfile(signer):
            return objcopy, signer
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if objcopy and signer and os.path.isfile(objcopy) and os.path.isfile(signer):
            return objcopy, signer
        raise ConanException("HarmonyOS binary signing tools are unavailable")

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return
        objcopy, signer = self._signing_tools()
        subprocess.run([objcopy, "--remove-section", ".codesign", path], check=True, timeout=30)
        signed = path + ".signed"
        result = subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                                 "-selfSign", "1"], capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not os.path.isfile(signed):
            raise ConanException("HarmonyOS signing failed: " + result.stderr[-1000:])
        shutil.move(signed, path)
        # The signer writes a new file without the executable bit. Cucumber
        # then fails with EACCES before any scenario can start.
        os.chmod(path, 0o755)

    def _prepare_cucumber_gems(self, test_dir):
        prepared = os.path.join(test_dir, "vendor", "prepared")
        if os.path.isdir(prepared):
            shutil.rmtree(prepared)
        os.makedirs(prepared)
        lib_dirs = []
        rows = self.conan_data.get("vendor_sources") or []
        if len(rows) != 18:
            raise ConanException("expected 18 Cucumber vendor sources, found %d" % len(rows))
        for row in rows:
            name = row["name"]
            version = str(row["version"])
            dest = os.path.join(prepared, "%s-%s" % (name, version))
            os.makedirs(dest)
            tree = row.get("tree")
            if tree:
                src = os.path.join(self.export_sources_folder, tree)
                if not os.path.isdir(os.path.join(src, "lib")):
                    raise ConanException("vendored Ruby tree missing: " + src)
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                # Conan extracts the tag archive. Ruby's rubygems unpacker
                # aborts with ILL on the CI Ruby, so this path stays in Python.
                get(self, row["url"], destination=dest,
                    filename="%s-%s.tar.gz" % (name, version),
                    sha256=row["sha256"], strip_root=True)
            # tag-expressions and cucumber-expressions tags keep the Ruby
            # tree under ruby/lib. The other tags put it at lib/.
            lib_dir = os.path.join(dest, row.get("lib", "lib"))
            if not os.path.isdir(lib_dir):
                raise ConanException("vendor source %s-%s has no lib directory" % (name, version))
            lib_dirs.append(lib_dir)
        cucumber_bin = os.path.join(prepared, "cucumber-3.1.2", "bin", "cucumber")
        if not os.path.isfile(cucumber_bin):
            raise ConanException("cucumber executable missing after vendor extract")
        script = os.path.join(prepared, "run-cucumber.sh")
        with open(script, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\n")
            handle.write("export RUBYLIB='%s'\n" % ":".join(lib_dirs))
            handle.write("exec ruby '%s' \"$@\"\n" % cucumber_bin)
        with open(os.path.join(prepared, "READY"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write("ok\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # cmake_minimum_required(2.6) is rejected by CMake 4 before the
        # toolchain file is read, so the floor has to be a configure -D.
        cmake.configure(
            build_script_folder=os.path.join(self.source_folder, "src"),
            variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

        executable = os.path.join(self.build_folder, "runtime", "tagutil")
        if not os.path.isfile(executable):
            raise ConanException("upstream build did not produce runtime/tagutil")
        self._sign_ohos_binary(executable)

        # Upstream Cucumber hard-codes ProjectRoot/build/tagutil. Run its
        # untouched test tree in this profile's build folder to avoid stale or
        # concurrently overwritten binaries in Conan's shared source folder.
        cucumber_root = os.path.join(self.build_folder, "cucumber-source")
        if os.path.isdir(cucumber_root):
            shutil.rmtree(cucumber_root)
        source_root = os.path.realpath(self.source_folder)
        build_root = os.path.realpath(self.build_folder)

        def ignore_source_build(directory, names):
            # basic_layout puts build-release inside the source folder. Copying
            # that child walks into cucumber-source and recurses until the path
            # exceeds NAME_MAX.
            if os.path.realpath(directory) != source_root:
                return []
            skipped = [name for name in (
                "build", "build-release", "build-debug", "cucumber-source")
                       if name in names]
            for name in names:
                if name in skipped:
                    continue
                candidate = os.path.realpath(os.path.join(directory, name))
                if candidate == build_root:
                    skipped.append(name)
            return skipped

        shutil.copytree(self.source_folder, cucumber_root,
                        ignore=ignore_source_build)
        cucumber_binary = os.path.join(cucumber_root, "build", "tagutil")
        os.makedirs(os.path.dirname(cucumber_binary), exist_ok=True)
        shutil.copy2(executable, cucumber_binary)
        os.chmod(cucumber_binary, 0o755)

        # CI Ruby 3.4.5 aborts with "ILL received in SEGV handler" inside
        # rubygems while it extracts archives (build #74913, package.rb
        # extract_tar_gz / copy_stream) and inside a Bundler thread pool
        # (build #74838, flock). Do not run `bundle install` or `make vendor`.
        # Fetch the pinned git tags with Conan and run the upstream cucumber
        # executable from those trees. The scenarios themselves are unchanged.
        self._prepare_cucumber_gems(os.path.join(cucumber_root, "test"))
        log_path = os.path.join(self.build_folder, "upstream-cucumber.log")
        with open(log_path, "w", encoding="utf-8") as log:
            self.run("make -C test", cwd=cucumber_root, env="conanbuild",
                     stdout=log, stderr=log, ignore_errors=True)
        with open(log_path, "r", encoding="utf-8", errors="replace") as log:
            output = log.read()
        self.output.info("Upstream test output (tail):\n" + "\n".join(output.splitlines()[-35:]))
        summaries = re.findall(r"(\d+) scenarios? \(([^)]*)\)", output)
        if len(summaries) != 1:
            raise ConanException(
                "expected one Cucumber scenario summary, found %d" % len(summaries))
        summary = summaries[0]
        discovered = int(summary[0])
        if discovered != self.expected_upstream_scenarios:
            raise ConanException(
                "expected %d Cucumber scenarios, found %d" %
                (self.expected_upstream_scenarios, discovered))
        passed = sum(int(n) for n in re.findall(r"(\d+) passed", summary[1]))
        failed = sum(int(n) for n in re.findall(r"(\d+) failed", summary[1]))
        skipped = sum(int(n) for n in re.findall(r"(\d+) pending", summary[1]))
        marker = {
            "status": "passed" if failed == 0 and passed == discovered else "failed",
            "framework": "Cucumber",
            "command": "make -C test",
            "discovered": discovered,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if marker["status"] != "passed":
            raise ConanException("upstream Cucumber tests failed or were skipped")
        with open(os.path.join(self.build_folder, "upstream-test-result.json"),
                  "w", encoding="utf-8") as result_file:
            json.dump(marker, result_file, ensure_ascii=False)

    def package(self):
        CMake(self).install()
        self._sign_ohos_binary(os.path.join(self.package_folder, "bin", "tagutil"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "blank.mp3", src=os.path.join(self.source_folder, "test", "files"),
             dst=os.path.join(self.package_folder, "share", "tagutil", "test-fixtures"))
        copy(self, "upstream-test-result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "tagutil"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
