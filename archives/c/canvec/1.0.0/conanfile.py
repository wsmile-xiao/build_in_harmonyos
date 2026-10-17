#!/usr/bin/env python3
"""Conan recipe for canvec 1.0.0 — CanVec shapefile extractor utility.

canvec is a pure Python script (single canvec.py, ~333 lines) that
navigates the CanVec data directory, extracts shapefiles matching a
search pattern from nested zip archives, and generates a
PostGIS-compatible SQL file via shp2pgsql.

Upstream: rskelly/canvec (GitHub), no tagged release — version 1.0.0
per task list; source pinned to commit ad2f25990f5 (2013-09-17 HEAD).

Build:  Python 2 → 3 syntax patch (except-as / print()), then install
        canvec.py as bin/canvec (python3 shebang wrapper).
Install: bin/canvec + canvec.py module.
Type:   application (CLI tool — commands.json declared at software level)

Deps:   standard library only (zipfile/os/re/subprocess/gzip/zlib) —
        no Conan dependencies. Runtime requires external `shp2pgsql`
        (PostGIS) on PATH when extracting real data; not needed for
        build or usage validation.

R26: Not applicable (no system-name collision).
R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CanvecConan(ConanFile):
    name = "canvec"
    version = "1.0.0"
    description = "CanVec shapefile extractor utility (PostGIS SQL generator)"
    license = "MIT"
    homepage = "https://github.com/rskelly/canvec"
    url = "https://github.com/rskelly/canvec"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

        # Upstream canvec.py is Python 2 syntax (2012-era script):
        #   except Exception, e:  ->  except Exception as e:
        #   print "..."           ->  print("...")
        # OHOS only ships python3 — patch before install.
        py_path = os.path.join(self.source_folder, "canvec.py")
        with open(py_path, "r", encoding="utf-8") as f:
            s = f.read()
        s = s.replace("except Exception, e:", "except Exception as e:")
        s = s.replace('print "Failed to open {0}: {1}.".format(f, e.__str__())',
                      'print("Failed to open {0}: {1}.".format(f, e.__str__()))')
        s = s.replace('print "Done"', 'print("Done")')
        # Usage block (print statements at __main__).
        s = s.replace('print "Usage: python canvec.py <pattern> <sqlfile> <canvecdir> <tablename> [schemaname] [tmpdir]\\n"',
                      'print("Usage: python canvec.py <pattern> <sqlfile> <canvecdir> <tablename> [schemaname] [tmpdir]\\n")')
        s = s.replace('print " pattern     - A pattern term to use against the shapefile names."',
                      'print(" pattern     - A pattern term to use against the shapefile names.")')
        s = s.replace('print " sqlfile    - A file to write the SQL to."',
                      'print(" sqlfile    - A file to write the SQL to.")')
        s = s.replace('print " canvecdir  - The directory where the canvec archives are located."',
                      'print(" canvecdir  - The directory where the canvec archives are located.")')
        s = s.replace('print " tablename  - The name of the database table."',
                      'print(" tablename  - The name of the database table.")')
        s = s.replace('print " schemaname - The name of the database schema. Defaults to \'public\'"',
                      'print(" schemaname - The name of the database schema. Defaults to \'public\'")')
        s = s.replace('print " tmpdir     - A temporary directory for extracting the canvec files. Defaults to \'/tmp\'"',
                      'print(" tmpdir     - A temporary directory for extracting the canvec files. Defaults to \'/tmp\'")')
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(s)

        # Syntax check the patched script (py3).
        self.run(f'python3 -m py_compile {py_path}', env="conanbuild")

    def package(self):
        copy(self, "canvec.py", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # bin/canvec wrapper with python3 shebang.
        wrapper = os.path.join(self.package_folder, "bin", "canvec")
        os.makedirs(os.path.dirname(wrapper), exist_ok=True)
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python3\n"
                    "import os, sys\n"
                    "sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'lib'))\n"
                    "exec(compile(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'lib', 'canvec.py'), encoding='utf-8').read(), 'canvec.py', 'exec'))\n")
        os.chmod(wrapper, 0o755)

    def package_info(self):
        self.output.info("canvec 1.0.0: bin/canvec (Python 3 script)")
        # R38 — CLI tool
        self.conf_info.define("user.tools.canvec:exe", "canvec")
