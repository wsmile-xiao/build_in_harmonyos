#!/usr/bin/env python3
"""Conan 2 recipe — libkysdk-applications 3.0.1.2.1 (HarmonyOS PC / OHOS aarch64).

Qt6 build of the openKylin ``kysdk`` application-level SDK.  This revision is a
*pure* re-target of the published Qt5 build (``libkysdk-applications/3.0.1.2``,
which requires ``qt5-qtbase/5.15.2.2``) onto the Qt6 stack used by the
openKylin/UKUI network applet ``kylin-nm-plugin/4.0.0.1``.

Why this package exists
-----------------------
``kylin-nm-plugin`` is a Qt6/qmake desktop applet whose ``.pro`` files declare
``PKGCONFIG += kysdk-applications`` and whose sources do ``using namespace kdk;``
and really use the UKUI widget classes (``KSwitchButton``,
``KBorderlessButton``, ``KTabBar``, ``KPasswordEdit``, ``KDialog``).  Because
those classes derive from Qt widget classes, a Qt5-compiled kysdk is
ABI-incompatible with a Qt6 consumer — hence a Qt6 build is mandatory.

Qt6 base
--------
``qtbase-sql-dbus/6.11.1`` (``FEATURE_dbus=ON`` + ``FEATURE_sql=ON``) — the same
Qt 6 base the sibling packages ``kylin-nm-base``, ``networkmanager-qt``,
``kylin-keyring`` and the plugin itself are built against.  Plain
``qtbase/6.11.1`` has ``FEATURE_dbus=OFF`` and would break ``QT += dbus``.
``qtsvg/6.11.1`` supplies Qt6Svg (SVG icon rendering) and ``gsettings-qt/1.1.1``
supplies the Qt6 QGSettings bindings.  No Qt5 dependency remains.

Build system
------------
Qt **qmake** (``qmake6`` from the Qt 6 base).  After the portability patches the
top-level ``kysdk-application.pro`` builds four sub-projects::

    kysdk-widgetutils   libkysdk-widgetutils.so
    kysdk-qtwidgets     libkysdk-qtwidgets.so   <- the kdk:: widget set
    kysdk-alm           libkysdk-alm.so
    kysdk-ukenv         libkysdk-ukenv.so

Install layout (upstream parity, fully relocatable — nothing under ``/usr``)::

    lib/libkysdk-*.so*
    include/kysdk/applications/*.h          <- #include <kwidget.h>
    lib/pkgconfig/kysdk-applications.pc     <- pkg-config module
    lib/pkgconfig/kysdk-qtwidgets.pc (+ alma/ukenv/widgetutils)

``includedirs`` carries *both* ``include`` and ``include/kysdk/applications`` so
that the flat upstream spelling (``#include <kwidget.h>``) and the prefixed one
(``#include <kysdk/applications/kwidget.h>``) both resolve.

Patches
-------
* ``0001``-``0005``: OHOS portability patches.  They cut *only* dependency chains
  that are genuinely absent on HarmonyOS PC — wayland-helper / kabase /
  appconf2, X11 / xcb / KWindowEffects / UKUI-decoration / wayland-helper inside
  qtwidgets, the KF6WindowSystem use inside alm, and the matching tests.  The
  Qt6 capabilities that the Qt5-era variants of these patches used to drop on a
  false "OHOS has no Qt5 …" premise (accessibility name/description, Qt6Svg
  icon rendering, Qt6Sql, ``QPalette::Accent``, QGSettings) are **restored** —
  see ``notes.md`` § "Restored Qt6 capabilities".
* ``0006``-``00NN``: the Qt6 API/ABI port (generated with ``refresh-patch
  --auto``): ``QWidget::enterEvent`` now takes ``QEnterEvent*`` and
  ``QLabel::pixmap()`` returns a ``QPixmap`` by value.  The two *public* headers
  (``kswitchbutton.h``, ``themeController.h``) do not expose QGSettings — the
  former drops the include, the latter uses a forward declaration — so that
  consumers never need gsettings-qt to compile ``<kwidget.h>``.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout

# Modules that survive the Qt6/OHOS port (== the ones shipped by 3.0.1.2).
MODULES = ("kysdk-widgetutils", "kysdk-qtwidgets", "kysdk-alm", "kysdk-ukenv")

# Public headers must live where the upstream .pro files install them:
#   headers.path = /usr/include/kysdk/applications/
HEADER_SUBDIR = os.path.join("include", "kysdk", "applications")


class LibkysdkApplicationsConan(ConanFile):
    name = "libkysdk-applications"
    version = "3.0.1.2.1"
    description = ("kylin SDK based on application level (Qt6 build): Qt extension "
                   "controls (kdk:: widget set), window management, process control, "
                   "display control, D-Bus call, gsetting acquisition modules")
    license = "LGPL-3.0"
    homepage = "https://gitee.com/openkylin/libkysdk-applications"
    url = "https://gitee.com/openkylin/libkysdk-applications"

    # Only shared objects are produced -> plain shared library package (R38: no
    # commands.json).
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Qt 6 base with FEATURE_dbus=ON + FEATURE_sql=ON (provides
        # Qt6Core/Gui/Widgets/Network/DBus/Sql in one prefix).
        self.requires("qtbase-sql-dbus/6.11.1")
        # Qt6Svg — used by the date-edit widgets' SVG icon rendering
        # (qtsvg/6.11.1 also pulls the plain qtbase/6.11.1, exactly like the
        # sibling recipes kirigami/6.18.0 and kshisen/26.04.0 do).
        self.requires("qtsvg/6.11.1")
        # QGSettings (Qt6 bindings to GSettings) — used by the theme controller,
        # the ukenv settings monitor and the widgetutils compositor probe.
        self.requires("gsettings-qt/1.1.1")

    def validate(self):
        # R32: never compare against a single OS literal.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"], sha256=source_data["sha256"],
            strip_root=True, destination=self.source_folder)

    # ── helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_headers(pro_path):
        """Return the ``HEADERS +=`` list of a .pro file (relocatable paths).

        Entries that are not ``*.h`` are dropped so only real public headers are
        installed (upstream lists a few non-header entries in ``HEADERS``).
        """
        entries = []
        collecting = False
        with open(pro_path, encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not collecting:
                    if line.startswith("HEADERS") and "+=" in line:
                        collecting = True
                        line = line.split("+=", 1)[1].strip()
                    else:
                        continue
                if line.endswith("\\"):
                    line = line[:-1].strip()
                    if line:
                        entries.append(line)
                    continue
                if line:
                    entries.append(line)
                collecting = False
        return [entry for entry in entries if entry.endswith(".h")]

    def _pc_text(self, name, description, libs):
        flags = " ".join(f"-l{lib}" for lib in libs)
        return (
            "prefix=${pcfiledir}/../..\n"
            "exec_prefix=${prefix}\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            f"Name: {name}\n"
            f"Description: {description}\n"
            f"Version: {self.version}\n"
            f"Libs: -L${{libdir}} {flags}\n"
            f"Cflags: -I${{includedir}} -I${{includedir}}/kysdk/applications\n"
        )

    # ── build ───────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)

        qtbase = self.dependencies["qtbase-sql-dbus"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake6")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration(
                "qtbase-sql-dbus/6.11.1 does not provide bin/qmake6"
            )

        spec_dir = os.path.join(qtbase.package_folder, "mkspecs", "harmonyos-clang")
        spec_args = "-spec harmonyos-clang" if os.path.isdir(spec_dir) else ""

        # R33: never rely on ambient shell variables — the Qt 6 toolchain is
        # injected explicitly through the Conan environment.  LD_LIBRARY_PATH
        # puts the Qt 6 prefix this package actually uses first so qmake6 loads
        # the matching libQt6Core (and therefore reads the right qt_lib_*.pri).
        env = Environment()
        env.define("QTDIR", qtbase.package_folder)
        env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))

        # Qt6Svg and gsettings-qt live in their own Conan packages, so their
        # include/library prefixes are handed to qmake through environment
        # variables (the .pro files turn them into INCLUDEPATH/LIBS).  Going via
        # pkg-config is not possible here: Qt6Svg is a Conan package whose module
        # .pri resolves its include base against the qtbase prefix, and the
        # Qt6Core/Gui .pc files shipped inside qtbase-sql-dbus still carry the
        # stale absolute prefix of the machine that built Qt.
        svg = self.dependencies["qtsvg"].package_folder
        env.define("KYSDK_QTSVG_INCLUDE", os.path.join(svg, "include"))
        env.define("KYSDK_QTSVG_LIBDIR", os.path.join(svg, "lib"))

        # gsettings-qt installs its header (and the `QGSettings` forwarding
        # header) under <prefix>/include/<arch>/qt6/QGSettings; cpp_info carries
        # exactly that directory.
        gsettings = self.dependencies["gsettings-qt"]
        env.define("KYSDK_GSETTINGS_INCLUDE",
                   os.path.join(gsettings.package_folder,
                                gsettings.cpp_info.includedirs[0]))
        env.define("KYSDK_GSETTINGS_LIBDIR",
                   os.path.join(gsettings.package_folder, "lib"))

        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
        pro = os.path.join(self.source_folder, "kysdk-application.pro")
        with env.vars(self).apply():
            # Out-of-source (shadow) build inside the Conan build folder so the
            # source tree stays pristine.
            self.run(f'cd "{self.build_folder}" && '
                     f'{shlex.quote(qmake)} {shlex.quote(pro)} {spec_args}')
            self.run(f'cd "{self.build_folder}" && make -j{jobs}')

    # ── package ─────────────────────────────────────────────────────────────
    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, HEADER_SUBDIR)

        # 1) shared objects produced by the four sub-projects
        for module in MODULES:
            search = os.path.join(self.build_folder, module)
            copy(self, "*.so*", src=search, dst=libdir, keep_path=False)

        # 2) public headers, installed flat exactly like upstream
        #    (headers.path = /usr/include/kysdk/applications/)
        for module in MODULES:
            pro = os.path.join(self.source_folder, module, f"{module}.pro")
            for rel in self._parse_headers(pro):
                src = os.path.join(self.source_folder, module, rel)
                if os.path.isfile(src):
                    copy(self, os.path.basename(rel), src=os.path.dirname(src),
                         dst=incdir, keep_path=False)

        # 3) pkg-config modules (relocatable, nothing hard-wired to /usr)
        pcdir = os.path.join(libdir, "pkgconfig")
        save(self, os.path.join(pcdir, "kysdk-applications.pc"), self._pc_text(
            "kysdk-applications",
            "openKylin kdk application-level widgets (Qt6 build)",
            [m for m in MODULES]))
        for module in MODULES:
            save(self, os.path.join(pcdir, f"{module}.pc"), self._pc_text(
                module, f"openKylin {module} (Qt6 build)", [module]))

        # 4) HMDFS trims the "other" permission bits on directory inheritance
        #    (755 -> 750); re-assert 0755 as the owning context so the artifacts
        #    stay loadable for any app uid.  Silent no-op elsewhere.
        for root, _, files in os.walk(libdir):
            for name in files:
                if ".so" in name:
                    try:
                        os.chmod(os.path.join(root, name), 0o755)
                    except OSError as exc:
                        self.output.warning(f"chmod {name}: {exc}")

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        # Both spellings must resolve for consumers:
        #   #include <kwidget.h>                 -> -I<prefix>/include/kysdk/applications
        #   #include <kysdk/applications/...>    -> -I<prefix>/include
        self.cpp_info.includedirs = [
            "include",
            os.path.join("include", "kysdk", "applications"),
        ]
        self.cpp_info.libs = list(MODULES)
        # Name the pkg-config module the downstream .pro files ask for
        # (PKGCONFIG += kysdk-applications).
        self.cpp_info.set_property("pkg_config_name", "kysdk-applications")
        # Qt 6 components this library links against (qtbase-sql-dbus exposes
        # core/gui/widgets/network/xml as Conan components; Qt6DBus and Qt6Sql
        # live in the same prefix and are pulled in by the consumer's own
        # `QT += dbus/sql`, exactly like the sibling Qt 6 recipes do).
        self.cpp_info.requires = [
            "qtbase-sql-dbus::core",
            "qtbase-sql-dbus::gui",
            "qtbase-sql-dbus::widgets",
            "qtbase-sql-dbus::network",
            "qtsvg::svg",
            "gsettings-qt::gsettings-qt",
        ]
        if self.settings.os == "OHOS":
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
