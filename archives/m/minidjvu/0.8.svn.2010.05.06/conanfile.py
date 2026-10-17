import hashlib
import html.parser
import os
import pathlib
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class _SvnDirectoryParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if href and href != "../" and not href.startswith(("/", "?", "#")):
            self.links.append(href)


class MinidjvuConan(ConanFile):
    name = "minidjvu"
    version = "0.8.svn.2010.05.06"
    description = "Bitonal DjVu encoder, decoder, library, and command-line tool"
    license = "GPL-3.0-or-later"
    homepage = "https://minidjvu.sourceforge.net/"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libtiff/4.7.2")

    def layout(self):
        # Upstream's custom Makefile.in installs headers by entering the source
        # tree, so this old Autotools project must be built in source.
        self.folders.source = "src"
        self.folders.build = "src"
        self.folders.generators = "conan"

    def source(self):
        source_data = self.conan_data["sources"]
        base_url = source_data["url"]
        if isinstance(base_url, list):
            base_url = base_url[-1]
        # CI's generic archive pre-downloader may replace a reachable SVN
        # directory URL with a cached HTML file. Reconstruct the same official,
        # revision-pinned URL in that case; no mirror or mutable HEAD is used.
        if base_url.startswith("file://"):
            base_url = (
                f"https://{source_data['repository']}/!svn/rvr/"
                f"{source_data['revision']}/{source_data['path']}/"
            )
        base_url = base_url.rstrip("/") + "/"

        def fetch(url):
            last_error = None
            for attempt in range(3):
                try:
                    request = urllib.request.Request(
                        url, headers={"User-Agent": "Conan/minidjvu-source"}
                    )
                    with urllib.request.urlopen(request, timeout=60) as response:
                        return response.read()
                except Exception as error:
                    last_error = error
                    time.sleep(attempt + 1)
            raise ConanException(f"Unable to download official SVN source: {url}: {last_error}")

        files = []

        def walk(relative=""):
            parser = _SvnDirectoryParser()
            directory_url = base_url + urllib.parse.quote(relative, safe="/")
            parser.feed(fetch(directory_url).decode("utf-8"))
            for link in parser.links:
                child = relative + link
                if link.endswith("/"):
                    walk(child)
                else:
                    files.append(child)

        walk()
        source_root = pathlib.Path(self.source_folder)
        source_root.mkdir(parents=True, exist_ok=True)

        def download_file(relative):
            data = fetch(base_url + urllib.parse.quote(relative, safe="/"))
            destination = source_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(download_file, files))

        digest = hashlib.sha256()
        for source_file in sorted(source_root.rglob("*")):
            if source_file.is_file():
                relative = source_file.relative_to(source_root).as_posix().encode()
                digest.update(relative)
                digest.update(b"\0")
                digest.update(source_file.read_bytes())
                digest.update(b"\0")
        if digest.hexdigest() != source_data["sha256"]:
            raise ConanException(
                "Official SVN r23 source tree checksum mismatch: "
                f"{digest.hexdigest()}"
            )

        for executable in (
            "configure",
            "libtool",
            "waf",
            "config/config.guess",
            "config/config.sub",
            "config/install-sh",
            "config/ltmain.sh",
        ):
            path = source_root / executable
            path.chmod(path.stat().st_mode | 0o111)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-static",
        ])
        tc.generate()

    def _runtime_env(self):
        env = Environment()
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        os.chmod(configure, os.stat(configure).st_mode | 0o111)
        autotools = Autotools(self)
        with self._runtime_env().vars(self).apply():
            autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["minidjvu"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["libtiff::libtiff"]
        self.cpp_info.set_property("cmake_file_name", "minidjvu")
        self.cpp_info.set_property("cmake_target_name", "minidjvu::minidjvu")
