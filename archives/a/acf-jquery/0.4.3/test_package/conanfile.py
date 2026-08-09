#!/usr/bin/env python3
"""Conan test_package — acf-jquery 0.4.3

L1 smoke test: verify the jquery asset bundle is installed in the package
(js libs in share/acf/app, widgets/parsers subdirs, tablesorter theme assets
in share/acf/www/skins/static/tablesorter).
"""
import os
import shutil

from conan import ConanFile


class AcfJqueryTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["acf-jquery"].package_folder

        # L0d: run a real test program via self.run() — test_jquery.sh
        # verifies the installed jquery assets (js libs, widgets/parsers
        # subdirs, tablesorter theme css/png).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_jquery.sh")
        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )

        appdir = os.path.join(pkg_folder, "share", "acf", "app")
        staticdir = os.path.join(pkg_folder, "share", "acf", "www", "skins", "static")

        self.output.info(f"ACF app dir: {appdir}")
        if not os.path.isdir(appdir):
            raise AssertionError(f"ACF app dir not found: {appdir}")

        # Core jquery libs (APP_DIST *.js)
        required_js = [
            "jquery-latest.js",
            "jquery.flot.js",
            "jquery.flot.time.js",
            "jquery.tablesorter.js",
            "jquery.tablesorter.widgets.js",
            "excanvas.js",
        ]
        for name in required_js:
            f = os.path.join(appdir, name)
            if not os.path.isfile(f):
                raise AssertionError(f"Required js file missing: {f}")
            self.output.info(f"  [ok] {name}")

        # Subdirs (APP_DIST widgets/*.js parsers/*.js)
        for sub in ("widgets", "parsers"):
            d = os.path.join(appdir, sub)
            if not os.path.isdir(d):
                raise AssertionError(f"Required subdir missing: {d}")
            files = [n for n in os.listdir(d) if n.endswith(".js")]
            if not files:
                raise AssertionError(f"No js files in {d}")
            self.output.info(f"  [ok] {sub}/ ({len(files)} js files)")

        # STATIC_DIST tablesorter theme assets
        tsdir = os.path.join(staticdir, "tablesorter")
        if not os.path.isdir(tsdir):
            raise AssertionError(f"tablesorter theme dir not found: {tsdir}")
        theme_files = [n for n in os.listdir(tsdir) if n.endswith(".css") or n.endswith(".png")]
        if not theme_files:
            raise AssertionError(f"No css/png assets in {tsdir}")
        self.output.info(f"  [ok] tablesorter/ ({len(theme_files)} css/png assets)")
