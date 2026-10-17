"""Fontconfig 2.18.3.3: relocatable target font configuration delivery."""
import glob
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building, can_run
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.env import Environment


class FontconfigConan(ConanFile):
    name = "fontconfig"
    version = "2.18.3.3"
    package_type = "library"
    description = "Font configuration, discovery and matching library"
    license = "MIT"
    homepage = "https://www.freedesktop.org/wiki/Software/fontconfig/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("expat/2.8.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "xml-backend": "expat", "doc": "disabled", "nls": "disabled",
            "tests": "enabled", "tools": "enabled", "cache-build": "disabled",
        })
        if self.settings.os == "OHOS":
            tc.project_options["default-fonts-dirs"] = ["/system/fonts"]
            tc.project_options["additional-fonts-dirs"] = []
        tc.generate()
        # Bind the archiver through Meson's file, not a release-worker shell.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if self.settings.os == "OHOS":
            compilers = dict(compilers)
            for key in ("ar", "ranlib"):
                compilers[key] = self._archive_tool(key, compilers)
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as stream:
                text = stream.read()
            if self.settings.os == "OHOS":
                text = "\n".join(line for line in text.splitlines()
                                 if not re.match(r"^\s*(ar|ranlib)\s*=", line)) + "\n"
            additions = []
            for key in ("ar", "ranlib"):
                value = compilers.get(key)
                if value and not any(line.strip().startswith(key + " =")
                                     for line in text.splitlines()):
                    escaped = value.replace("\\", "/").replace("'", "\\'")
                    additions.append("%s = '%s'" % (key, escaped))
            if additions:
                if text.count("[binaries]") != 1:
                    raise ConanException("Missing/duplicate Meson binaries section")
                text = text.replace("[binaries]", "[binaries]\n" + "\n".join(additions), 1)
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(text)

    def _archive_tool(self, key, compilers):
        # Meson invokes these through Python, whose native posix_spawn does
        # not reliably search PATH. Bind a real executable, never a bare name.
        def resolve(value):
            path = value if os.path.isabs(value) else shutil.which(value)
            if path:
                path = os.path.realpath(path)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
            return None

        explicit = compilers.get(key)
        if explicit:
            path = resolve(explicit)
            if not path:
                raise ConanException("Configured archive tool is not executable: " + explicit)
            return path
        compiler = resolve(compilers.get("c") or "clang")
        if not compiler:
            raise ConanException("Cannot resolve configured C compiler for archive tools")
        tool = "llvm-" + key
        probe = subprocess.run(
            [compiler, "-print-prog-name=" + tool], stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=15, check=True,
        )
        candidates = [probe.stdout.strip()]
        stem, extension = os.path.splitext(os.path.basename(compiler))
        suffix = re.search(r"(-[0-9]+)$", stem)
        for name in ((tool + suffix.group(1)) if suffix else tool, tool):
            candidates.append(os.path.join(os.path.dirname(compiler), name + extension))
        candidates.append(tool)
        for candidate in candidates:
            path = resolve(candidate) if candidate else None
            if path:
                return path
        raise ConanException("Cannot resolve executable archive tool: " + tool)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        if os.name == "nt" and self.settings.os == "OHOS" and cross_building(self):
            # Conan's Windows helper normalizes '/' to the host drive root.
            # Meson validates a cross target's prefix using POSIX semantics.
            machine = os.path.join(self.generators_folder, MesonToolchain.cross_filename)
            if not os.path.isfile(machine):
                raise ConanException("Required Meson cross machine file is missing")
            extra = self.conf.get("tools.meson.mesontoolchain:extra_machine_files",
                                  default=[], check_type=list)
            files = [machine] + extra
            command = "meson setup " + " ".join('--cross-file "%s"' % p for p in files)
            native = os.path.join(self.generators_folder, MesonToolchain.native_filename)
            if os.path.isfile(native):
                command += ' --native-file "%s"' % native
            command += ' "%s" "%s" --prefix=/' % (self.build_folder, self.source_folder)
            self.run(command)
        else:
            meson.configure()
        meson.build()
        if can_run(self):
            environment = Environment()
            if self.settings.os == "OHOS":
                temporary = os.path.join(self.build_folder, "upstream-private-tmp")
                os.makedirs(temporary, exist_ok=True)
                environment.define_path("TMPDIR", temporary)
                environment.define("FC_TEST_DIRECTORY_VIEW", "1")
            with environment.vars(self).apply():
                # Meson's test-only dependencies (including external font
                # fixtures) are not part of the default build. Let the test
                # runner materialize them before collecting upstream cases.
                self.run('meson test -v -C "%s"' % self.build_folder)
        else:
            self.output.warning("Upstream tests built; target execution still required")

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS":
            self._relocate_configuration()
            if not cross_building(self):
                self._sign_runtime_artifacts()

    def _relocate_configuration(self):
        root = os.path.realpath(self.package_folder)
        config_dir = os.path.join(root, "etc", "fonts")
        config = os.path.join(config_dir, "fonts.conf")
        if not os.path.isfile(config) or os.path.islink(config):
            raise ConanException("Installed regular fonts.conf is required")
        document = ET.parse(config)
        element = document.getroot()
        if element.tag != "fontconfig":
            raise ConanException("Unexpected fontconfig XML root")
        includes = element.findall("include")
        if len(includes) != 1 or (includes[0].text or "").strip() != "conf.d":
            raise ConanException("Expected upstream relative conf.d include")
        for tag in ("dir", "cachedir"):
            for child in list(element.findall(tag)):
                element.remove(child)
        ET.SubElement(element, "dir").text = "/system/fonts"
        ET.SubElement(element, "dir", {"prefix": "xdg"}).text = "fonts"
        ET.SubElement(element, "cachedir", {"prefix": "xdg"}).text = "fontconfig"
        # Keep upstream aliases and enabled substitution rules. Materialize only
        # the enabled template links, not every mutually exclusive conf.avail rule.
        active = os.path.join(config_dir, "conf.d")
        templates = os.path.join(root, "share", "fontconfig", "conf.avail")
        if os.path.islink(active) or not os.path.isdir(active):
            raise ConanException("Regular installed conf.d directory is required")
        replacements = []
        for name in sorted(os.listdir(active)):
            path = os.path.join(active, name)
            if not name.endswith(".conf") or not os.path.islink(path):
                continue
            target = os.readlink(path)
            if os.path.basename(target) != name:
                raise ConanException("Enabled config link changes basename: " + name)
            source = os.path.join(templates, name)
            if not os.path.isfile(source) or os.path.islink(source):
                raise ConanException("Missing regular packaged config template: " + name)
            replacements.append((path, source))
        # Validate the whole replacement set before mutating the package.
        for path, source in replacements:
            os.unlink(path)
            shutil.copyfile(source, path)
        with open(config, "w", encoding="utf-8", newline="\n") as stream:
            stream.write('<?xml version="1.0"?>\n')
            stream.write('<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n')
            stream.write(ET.tostring(element, encoding="unicode"))
            stream.write("\n")

    def _sign_runtime_artifacts(self):
        objcopy = self.conf.get("user.fontconfig:objcopy", default="/data/service/hnp/bin/llvm-objcopy")
        signer = self.conf.get("user.fontconfig:signer", default="/data/service/hnp/bin/binary-sign-tool")
        paths = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
        # Installation can copy a link-time signed ELF and change its layout.
        # Sign the final installed tools as well as the shared libraries.
        paths += glob.glob(os.path.join(self.package_folder, "bin", "*"))
        for path in sorted(set(os.path.realpath(p) for p in paths if os.path.isfile(p))):
            if os.path.commonpath([os.path.realpath(self.package_folder), path]) != os.path.realpath(self.package_folder):
                raise ConanException("Runtime artifact escapes the package")
            with open(path, "rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    continue
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, path, path))
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["fontconfig"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "fontconfig")
        self.cpp_info.set_property("cmake_target_name", "fontconfig::fontconfig")
        self.cpp_info.set_property("pkg_config_name", "fontconfig")
        if self.settings.os == "OHOS":
            config_dir = os.path.join(self.package_folder, "etc", "fonts")
            self.runenv_info.define_path("FONTCONFIG_PATH", config_dir)
            self.runenv_info.define_path("FONTCONFIG_FILE", os.path.join(config_dir, "fonts.conf"))
            # XDG_CACHE_HOME belongs to the application, never the immutable package.
