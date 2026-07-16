#!/usr/bin/env python3
"""Conan recipe — pgformatter 5.10 (perl script)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class PgformatterConan(ConanFile):
    name = "pgformatter"
    version = "5.10"
    description = "pgFormatter — PostgreSQL SQL and PL/PGSQL syntax beautifier"
    license = "PostgreSQL"
    homepage = "https://github.com/darold/pgFormatter"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pg_format is a self-contained perl script, no compilation needed
        pass

    def _get_perl(self):
        """Find perl interpreter at runtime (no PATH dependency)."""
        import shutil as _shutil
        perl_env = os.environ.get("PERL")
        if perl_env and os.path.isfile(perl_env):
            return perl_env
        # Check known OHOS locations directly
        for p in ["/data/service/hnp/bin/perl", "/usr/bin/perl", "/usr/local/bin/perl"]:
            if os.path.isfile(p):
                return p
        # Try PATH as last resort
        found = _shutil.which("perl")
        if found:
            return found
        return None

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        # pg_format uses `use lib "$FindBin::RealBin/lib"`, so the lib/ dir
        # must sit right next to the script inside bin/.
        copy(self, "pg_format", self.source_folder, bin_dir)
        copy(self, "*", os.path.join(self.source_folder, "lib"),
             os.path.join(bin_dir, "lib"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "pgformatter"))
        copy(self, "README", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "pgformatter"))

        # OHOS: the original "#!/usr/bin/env perl" shebang can fail at
        # runtime because /usr/bin/env may be unavailable on HarmonyOS PC.
        # Hardcoding "/usr/bin/perl" was also wrong — that path does not
        # exist on the CI worker (perl actually lives at e.g.
        # /data/service/hnp/bin/perl), causing "bad interpreter: No such
        # file or directory". So probe for the real perl path at build time
        # (same approach as perl-sql-abstract) and always rewrite the
        # shebang. If no perl is found anywhere, fall back to the
        # conventional "/usr/bin/perl" instead of keeping the possibly
        # unavailable env shebang.
        perl = self._get_perl() or "/usr/bin/perl"
        pg = os.path.join(bin_dir, "pg_format")
        with open(pg, "r") as f:
            content = f.read()
        content = content.replace("#!/usr/bin/env perl", "#!" + perl, 1)
        with open(pg, "w") as f:
            f.write(content)
        os.chmod(pg, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
