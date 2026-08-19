from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import hashlib
import json
import os
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse


class AllowHtmlTempConan(ConanFile):
    name = "allow-html-temp"
    version = "10.1.1"
    description = "Thunderbird extension for temporarily displaying HTML message content"
    license = "MPL-2.0"
    homepage = "https://gitlab.com/ThunderbirdMailDE/allow-html-temp"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    @staticmethod
    def _w3_safe_url(url):
        return url.replace("%", "%25") if url.startswith("file://") else url

    def source(self):
        source = dict(self.conan_data["sources"])
        source["url"] = self._w3_safe_url(source["url"])
        parsed = urlparse(source["url"])
        if parsed.scheme == "file":
            expected = source["sha256"]
            requested = parsed.path
            cache_root = Path(requested)
            while cache_root.name != "predl_cache" and cache_root != cache_root.parent:
                cache_root = cache_root.parent
            candidates = []
            if os.path.isfile(requested):
                candidates.append(requested)
            if cache_root.name == "predl_cache" and cache_root.is_dir():
                for current, _, names in os.walk(cache_root):
                    candidates.extend(os.path.join(current, name) for name in names)
            project_cache = Path.cwd() / ".build-cache"
            if project_cache.is_dir():
                for current, _, names in os.walk(project_cache):
                    candidates.extend(os.path.join(current, name) for name in names)
            cached = next(
                (path for path in candidates if os.path.isfile(path)
                 and hashlib.sha256(open(path, "rb").read()).hexdigest() == expected),
                None,
            )
            if cached:
                with tarfile.open(cached, "r:gz") as archive:
                    archive.extractall(self.source_folder, filter="data")
                roots = [name for name in os.listdir(self.source_folder)
                         if os.path.isdir(os.path.join(self.source_folder, name))]
                if len(roots) == 1:
                    root = os.path.join(self.source_folder, roots[0])
                    for name in os.listdir(root):
                        os.replace(os.path.join(root, name), os.path.join(self.source_folder, name))
                    os.rmdir(root)
                return
        get(self, **source, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        manifest_path = os.path.join(self.source_folder, "manifest.json")
        with open(manifest_path, encoding="utf-8") as stream:
            manifest = json.load(stream)
        if manifest.get("version") != str(self.version):
            raise RuntimeError("manifest.json version does not match Conan version")

        output = os.path.join(self.build_folder, "allow-html-temp-10.1.1.xpi")
        roots = ("_locales", "api", "icons", "options", "scripts")
        files = ["LICENSE", "manifest.json"]
        for root_name in roots:
            root = os.path.join(self.source_folder, root_name)
            for current, dirs, names in os.walk(root):
                dirs.sort()
                for name in sorted(names):
                    files.append(os.path.relpath(os.path.join(current, name), self.source_folder))

        os.makedirs(self.build_folder, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative in sorted(files):
                source = os.path.join(self.source_folder, relative)
                info = zipfile.ZipInfo(relative.replace(os.sep, "/"), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                with open(source, "rb") as stream:
                    archive.writestr(info, stream.read())
        self.output.info(f"Created deterministic XPI with {len(files)} files")

    def package(self):
        extension_dir = os.path.join(self.package_folder, "share", "allow-html-temp")
        copy(self, "allow-html-temp-10.1.1.xpi", self.build_folder, extension_dir)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share/allow-html-temp"]
