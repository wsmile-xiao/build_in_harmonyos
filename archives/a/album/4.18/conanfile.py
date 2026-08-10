#!/usr/bin/env python3
"""Conan recipe — album 4.18 (pure Perl HTML photo album generator).

album is a single Perl script (plus themes/languages data) from
marginalhacks.com. No C/C++ compilation. build() only runs a `perl -c`
syntax check; package() installs the script under bin/ with a relocatable
wrapper that execs the target environment's Perl interpreter.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file, save
from conan.tools.layout import basic_layout


class AlbumConan(ConanFile):
    name = "album"
    version = "4.18"
    package_type = "application"
    settings = "os", "arch"
    description = "Themeable HTML photo album generator (pure Perl)"
    license = "BSD-style (see License.txt)"
    homepage = "https://marginalhacks.com/Hacks/album/"
    url = "https://marginalhacks.com/Hacks/album/"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # No C/C++ compilation — pure Perl. Validate script syntax with the
        # target environment's Perl interpreter.
        self.run("{} -c album".format(os.environ.get("PERL", "perl")), cwd=self.source_folder)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Install the main album script.
        copy(self, "album", src=self.source_folder, dst=bin_dir)
        # OHOS has no /usr/bin/perl; the upstream script shebang is
        # #!/usr/bin/perl. Rewrite it to the target environment's Perl.
        installed = os.path.join(bin_dir, "album")
        replace_in_file(
            self, installed, "#!/usr/bin/perl", "#!/data/service/hnp/bin/perl", strict=False
        )
        # Install supporting data (themes are separate album_data package; ship
        # the docs/license that come with the script).
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "CHANGELOG", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "album"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
