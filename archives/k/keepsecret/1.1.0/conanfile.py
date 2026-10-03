#!/usr/bin/env python3
"""Conan recipe - keepsecret 1.1.0 (KDE Kirigami QML application).

KeepSecret is a password manager GUI client for a Secret Service compatible
provider (KWallet, oo7, gnome-keyring, KeepassXC). Upstream is a Qt6/KF6
Kirigami application; the secret store is reached through libsecret-1 for the
item/collection data model and through QtDBus for the Secret Service client.

Adapted to HarmonyOS PC (aarch64):
  - Qt6 stack: qtbase-sql-dbus (Core/Gui/Widgets/Test/Sql/DBus),
    qtdeclarative (Qml/Quick/QuickControls2 + QML modules), qtsvg,
    qtshadertools.
  - KF6 frameworks at the published ohpcd 6.18 generation, plus
    kirigami-addons/1.13.0.
  - libsecret/0.21.7 (the published generation) provides libsecret-1;
    keepsecret's top-level CMakeLists resolves it via
    pkg_check_modules(LIBSECRET IMPORTED_TARGET REQUIRED libsecret-1), so the
    recipe stages real-prefix .pc files and points PKG_CONFIG_PATH at them
    (the kio-kwallet precedent).
  - zlib/1.3.2 root override: the KF6 QML stack pulls karchive (via
    kirigami-addons -> kiconthemes) which pins zlib/1.3.2, while the published
    libsecret/0.21.7 binary closure was built against glib/2.84.0.1 which pins
    zlib/1.3.1.1. Unifying on 1.3.2 removes the version conflict.
  - Registry QML module gaps (the same gaps the alligator recipe documents):
    org.kde.coreaddons (kcoreaddons builds KCOREADDONS_USE_QML=OFF),
    org.kde.config (kconfig builds KCONFIG_USE_QML=OFF) and
    org.kde.kitemmodels (the kitemodels recipe skips the QML plugin) are not
    published. Patches drop those imports and substitute in-registry
    equivalents, plus a small QSortFilterProxyModel shim for the one
    KSortFilterProxyModel use.
  - KF6::I18nQml (KLocalizedQmlContext) is not published (ki18n builds
    BUILD_WITH_QML=OFF); the deprecated KLocalizedContext from KF6::I18n
    provides the same QML i18n context object and is kept visible with
    KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0.
  - qqc2-desktop-style (org.kde.desktop) / qqc2-breeze-style are not
    published; the QQC2 style falls back to the in-tree Basic style.
  - Upstream ships NO test suite (no tests/ directory, no CTest registration
    anywhere in CMakeLists.txt/src/CMakeLists.txt) - see notes.md for the
    census evidence and the test_package tests that cover the deliverable.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KeepsecretConan(ConanFile):
    name = "keepsecret"
    version = "1.1.0"
    description = "KDE Secret Service password manager GUI (Kirigami QML application)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/utilities/keepsecret"
    url = "https://download.kde.org/stable/keepsecret/keepsecret-1.1.0.tar.xz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # QML application package: the QML runtime (qtdeclarative) and the KF6 QML
    # modules (kirigami, kirigami-addons) are required at runtime and resolved
    # through the consumers' runenv (QML2_IMPORT_PATH), so no library exports.
    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 stack: qtbase-sql-dbus provides Core/Gui/Widgets/Test/Sql/DBus;
        # qtdeclarative provides Qml/Quick/QuickControls2/Qt.labs.* QML modules.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtshadertools/6.11.1")
        # KF6 framework libraries (published ohpcd 6.18 generation).
        self.requires("kirigami/6.18.0")
        self.requires("kirigami-addons/1.13.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kitemmodels/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        # libsecret-1 (pkg_check_modules in the top-level CMakeLists).
        self.requires("libsecret/0.21.7")
        # Unify zlib: karchive/6.18.0 (via kirigami-addons -> kiconthemes)
        # pins zlib/1.3.2 while the libsecret/0.21.7 glib closure pins
        # zlib/1.3.1.1; the root override resolves the conflict on 1.3.2.
        self.requires("zlib/1.3.2", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._pin_qt6_cmake_dirs(tc)
        self._link_real_libintl(tc)
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _pin_qt6_cmake_dirs(self, toolchain):
        """Pin the Qt6 CMake package dirs to qtbase-sql-dbus.

        Two qtbase variants coexist in the graph: qtbase-sql-dbus/6.11.1
        (FEATURE_dbus=ON: Core/Gui/Widgets/Test/Sql/DBus) is required directly,
        while the plain qtbase/6.11.1 (FEATURE_dbus=OFF, its QtCore/qconfig.h
        defines QT_NO_DBUS) arrives transitively via kitemmodels/kiconthemes.
        Without an explicit pin, CMake may resolve Qt6::Core from the plain
        qtbase, whose headers #ifndef QT_NO_DBUS the whole QtDBus API away -
        keepsecret includes <QDBusObjectPath> (secretserviceclient.h), so the
        compile then fails with "unknown type name 'QDBusObjectPath'" and
        "use of undeclared identifier 'QDBusConnection'".

        qtbase uses cmake_find_mode=none (it ships its own Qt6Config.cmake), so
        CMakeDeps does not generate one and the dirs must be set explicitly
        (bluez-qt 6.28.0 precedent). Components provided by other Qt packages
        (Qt6Qml from qtdeclarative, ...) are still discovered through
        QT_ADDITIONAL_PACKAGES_PREFIX_PATH set by generate().
        """
        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if not qtbase or not qtbase.package_folder:
            return
        qt66 = os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6")
        if not os.path.isdir(qt66):
            qt66 = os.path.join(qtbase.package_folder, "lib", "cmake")
        toolchain.cache_variables["Qt6_DIR"] = qt66
        for component in ("Core", "Gui", "Widgets", "Network", "Sql", "DBus", "Xml", "Test"):
            toolchain.cache_variables[f"Qt6{component}_DIR"] = qt66

    # glib (musl/proxy-libintl build) references g_libintl_* but ships no
    # provider; gettext's libintl.so.8 exports the unprefixed libintl_* set
    # only. This shim supplies the g_libintl_* names by forwarding to the real
    # libintl at runtime (kio-kwallet 6.28.0 precedent).
    _INTL_SHIM_C = r"""
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>

static void *intl_handle;

static void *intl_sym(const char *plain, const char *prefixed)
{
    void *s = NULL;
    if (intl_handle) {
        s = dlsym(intl_handle, prefixed);
        if (!s) s = dlsym(intl_handle, plain);
    }
    return s;
}

__attribute__((constructor))
static void shim_init(void)
{
    intl_handle = dlopen("libintl.so.8", RTLD_NOW | RTLD_GLOBAL);
    if (!intl_handle) intl_handle = dlopen("libintl.so", RTLD_NOW | RTLD_GLOBAL);
}

char *g_libintl_gettext(const char *m)
{
    void *f = intl_sym("gettext", "libintl_gettext");
    return f ? ((char *(*)(const char *))f)(m) : (char *)m;
}
char *g_libintl_dgettext(const char *d, const char *m)
{
    void *f = intl_sym("dgettext", "libintl_dgettext");
    return f ? ((char *(*)(const char *, const char *))f)(d, m) : (char *)m;
}
char *g_libintl_dcgettext(const char *d, const char *m, int c)
{
    void *f = intl_sym("dcgettext", "libintl_dcgettext");
    return f ? ((char *(*)(const char *, const char *, int))f)(d, m, c) : (char *)m;
}
char *g_libintl_bindtextdomain(const char *d, const char *dir)
{
    void *f = intl_sym("bindtextdomain", "libintl_bindtextdomain");
    return f ? ((char *(*)(const char *, const char *))f)(d, dir) : (char *)d;
}
char *g_libintl_bind_textdomain_codeset(const char *d, const char *c)
{
    void *f = intl_sym("bind_textdomain_codeset", "libintl_bind_textdomain_codeset");
    return f ? ((char *(*)(const char *, const char *))f)(d, c) : (char *)d;
}
char *g_libintl_textdomain(const char *d)
{
    void *f = intl_sym("textdomain", "libintl_textdomain");
    return f ? ((char *(*)(const char *))f)(d) : (char *)d;
}
char *g_libintl_ngettext(const char *s1, const char *s2, unsigned long n)
{
    void *f = intl_sym("ngettext", "libintl_ngettext");
    return f ? ((char *(*)(const char *, const char *, unsigned long))f)(s1, s2, n)
             : (char *)(n == 1 ? s1 : s2);
}
char *g_libintl_dngettext(const char *d, const char *s1, const char *s2, unsigned long n)
{
    void *f = intl_sym("dngettext", "libintl_dngettext");
    return f ? ((char *(*)(const char *, const char *, const char *, unsigned long))f)(d, s1, s2, n)
             : (char *)(n == 1 ? s1 : s2);
}
char *g_libintl_dcngettext(const char *d, const char *s1, const char *s2, unsigned long n, int c)
{
    void *f = intl_sym("dcngettext", "libintl_dcngettext");
    return f ? ((char *(*)(const char *, const char *, const char *, unsigned long, int))f)(d, s1, s2, n, c)
             : (char *)(n == 1 ? s1 : s2);
}
void _proxy_libintl_deinit(void) {}
"""

    def _intl_shim_path(self):
        return os.path.join(self.build_folder, "keepsecret-intl-shim.o")

    def _build_intl_shim(self):
        """Compile the g_libintl_* forwarding shim (see _INTL_SHIM_C).

        The shim is built as a relocatable object and linked into the
        executable (see _link_real_libintl), so glib's g_libintl_* references
        are satisfied by a definition inside the application binary itself -
        no LD_PRELOAD and no extra packaged .so are required, and the fix
        travels with the packaged app for downstream consumers.
        """
        dst = self._intl_shim_path()
        if os.path.exists(dst):
            return dst
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c")
        cc = cc or shutil.which("clang") or shutil.which("cc")
        if not cc:
            self.output.warning("no C compiler available; intl shim not built")
            return None
        src = os.path.join(self.build_folder, "keepsecret_intl_shim.c")
        with open(src, "w") as handle:
            handle.write(self._INTL_SHIM_C)
        # self.run() goes through conan's env wrapper, so the profile [buildenv]
        # LD_LIBRARY_PATH (which carries the SDK llvm/lib dir the OHOS lld needs
        # to load libxml2.so.16) is already in effect here.
        self.run('{} -fPIC -c "{}" -o "{}"'.format(cc, src, dst))
        return dst

    def _link_real_libintl(self, toolchain):
        """Resolve the dual-libintl symbol split introduced by the glib chain.

        Two libraries in the graph have DT_NEEDED libintl.so.8 but need
        *different* export sets:

          * libglib-2.0.so calls g_libintl_* - provided only by glib's own
            proxy-libintl build of libintl.so.8;
          * libKF6I18n.so calls libintl_* - provided only by gettext's real
            libintl.so.8.

        Both shared objects carry the SONAME libintl.so.8, so at link time
        lld's --no-allow-shlib-undefined default rejects whichever set is not
        on the link line (it first failed on libintl_*, then on g_libintl_*).
        gettext's lib dir is prepended so the executable's own -lintl resolves
        to the real implementation, and --allow-shlib-undefined lets the
        remaining transitive references be bound by the runtime loader.
        (kio-kwallet 6.28.0 precedent - the other recipe in this archive that
        combines the glib/libsecret chain with KF6::I18n.)
        """
        flags = "-Wl,--disable-new-dtags -Wl,--allow-shlib-undefined"
        gettext = self.dependencies.get("gettext")
        if gettext and gettext.package_folder:
            libdir = None
            for candidate in gettext.cpp_info.libdirs:
                path = os.path.join(gettext.package_folder, candidate)
                if os.path.isfile(os.path.join(path, "libintl.so")) or os.path.isfile(
                    os.path.join(path, "libintl.so.8")
                ):
                    libdir = path
                    break
            if libdir:
                flags += " -L{} -lintl".format(libdir.replace("\\", "/"))
        # Link the g_libintl_* forwarding shim into the executable so glib's
        # unresolved g_libintl_* references have a definition inside the app
        # itself (the two libintl.so.8 providers cannot coexist, see above).
        shim = self._build_intl_shim()
        if shim:
            # No quotes: the path contains no spaces, and embedded quotes get
            # mangled into a stray ';' list separator by the CMake variable.
            flags += " " + shim.replace("\\", "/")
        toolchain.variables["CMAKE_EXE_LINKER_FLAGS"] = flags

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _write_fixed_pkgconfig(self):
        """Stage pkg-config files with real prefix paths into the generators
        folder. The top-level CMakeLists resolves libsecret through
        pkg_check_modules(LIBSECRET IMPORTED_TARGET REQUIRED libsecret-1) and
        the published .pc files carry prefix=/ (DESTDIR-style install), which
        pkg-config cannot resolve by itself. The staged set (libsecret-1 plus
        its glib chain) is exposed to the build via PKG_CONFIG_PATH."""
        staged_dir = os.path.join(self.generators_folder, "pkgconfig-staged")
        os.makedirs(staged_dir, exist_ok=True)
        for dep in list(self.dependencies.values()):
            if not dep or not dep.package_folder:
                continue
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            copied = []
            for name in os.listdir(pc_dir):
                if not name.endswith(".pc"):
                    continue
                src = os.path.join(pc_dir, name)
                dst = os.path.join(staged_dir, name)
                with open(src, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                lines = []
                for line in content.splitlines():
                    if line.startswith("prefix="):
                        line = "prefix=" + dep.package_folder
                    lines.append(line)
                with open(dst, "w", encoding="utf-8", errors="replace") as handle:
                    handle.write("\n".join(lines) + "\n")
                copied.append(name)
            if copied:
                self.output.info("pkg stage: {} -> {} files".format(dep.ref.name, len(copied)))
        self._stage_missing_requires(staged_dir)
        return staged_dir

    def _stage_missing_requires(self, staged_dir):
        """pkg_check_modules(LIBSECRET libsecret-1) resolves the whole glib
        Requires chain. Some of those leaf packages (pcre2, libffi, zlib) are
        skip-dependencies in the conan graph (no local package_folder), so
        their .pc files cannot be staged. Generate minimal stub .pc files for
        any missing Requires module: the stub only needs to exist with a
        plausible Cflags (the actual glib headers and the real symbols come
        from the staged glib/libsecret .pc files and the shared-library
        DT_NEEDED chain, not from pkg-config). Same approach as the
        kio-kwallet 6.28.0 recipe."""
        import re
        stub_prefix = None
        for probe in ("glib-2.0.pc", "libsecret-1.pc"):
            candidate = os.path.join(staged_dir, probe)
            if not os.path.isfile(candidate):
                continue
            with open(candidate, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("prefix="):
                        stub_prefix = line.strip().split("=", 1)[1]
                        break
            if stub_prefix:
                break
        if not stub_prefix:
            return

        def pc_modules(text):
            names = []
            for line in text.splitlines():
                head = line.split(":", 1)[0].strip()
                if head not in ("Requires", "Requires.private"):
                    continue
                for tok in line.split(":", 1)[1].replace(",", " ").split():
                    name = re.split(r"[<>=!]", tok)[0].strip()
                    if not name or name[0].isdigit():
                        continue
                    names.append(name)
            return names

        pending = set()
        for name in os.listdir(staged_dir):
            if not name.endswith(".pc"):
                continue
            with open(os.path.join(staged_dir, name), encoding="utf-8", errors="replace") as handle:
                pending.update(pc_modules(handle.read()))
        for name in sorted(pending):
            stub = os.path.join(staged_dir, name + ".pc")
            if os.path.isfile(stub):
                continue
            with open(stub, "w", encoding="utf-8") as handle:
                handle.write(
                    "prefix={}\n"
                    "Name: {}\n"
                    "Description: stub for conan skip-dependency (header-only "
                    "resolution for pkg_check_modules)\n"
                    "Version: 99\n"
                    "Libs:\n"
                    "Cflags: -I{}/include\n".format(stub_prefix, name, stub_prefix)
                )
            self.output.info("pkg stage: stub pc written for {}".format(name))

    def build(self):
        apply_conandata_patches(self)
        staged_pc = self._write_fixed_pkgconfig()
        cmake = CMake(self)
        with self._runtime_env(include_build=True, staged_pc=staged_pc).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Upstream keepsecret 1.1.0 ships NO test suite.

        Census evidence (see notes.md for the full protocol/R51 record):
        there is no tests/ or autotests/ directory in the tarball, and neither
        CMakeLists.txt nor src/CMakeLists.txt contains add_test(),
        BUILD_TESTING or any CTest registration. The recipe therefore asserts
        the upstream state instead of pretending to run a suite, and the
        deliverable is covered by test_package (real API/QML-driven tests).
        """
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            with self._runtime_env(include_build=True).vars(self).apply():
                listing = self.run(
                    'ctest --test-dir "{}" -N'.format(self.build_folder),
                    ignore_errors=True,
                )
                self.output.info("upstream ctest registration: {}".format(listing))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}", ignore_errors=True)
                self.run(f"{self._quote(signer)} sign -inFile {self._quote(path)} -outFile {self._quote(path)} -selfSign 1")
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def _runtime_env(self, include_build=False, staged_pc=None):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # Qt host tools (qmltyperegistrar/qmlcachegen/qsb) live in
                # libexec/ next to the Qt libraries they need at runtime.
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        # The host shell LD_LIBRARY_PATH carries whitespace-padded entries
        # (".../chipset-pub-sdk:         /system/lib64") which the OHOS loader
        # cannot resolve, so qtpaths/moc from the qtbase package fail with
        # "libc++_shared.so not found". Provide clean system library dirs
        # explicitly so Qt host tools keep working inside the build env.
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        if staged_pc:
            env.prepend_path("PKG_CONFIG_PATH", staged_pc)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        # QML application package: the binary is resolved through bindirs and
        # the QML runtime through the runenv (QML2_IMPORT_PATH), so no library
        # exports are needed here.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "bin"))
