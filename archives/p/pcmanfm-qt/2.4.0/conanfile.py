#!/usr/bin/env python3
"""Conan recipe — pcmanfm-qt 2.4.0.

pcmanfm-qt is the Qt6 file manager of LXQt. It is a CMake application built
against libfm-qt, Qt6 Widgets/DBus/LinguistTools and lxqt2-build-tools.

OHOS adaptation:
- qtbase 6.11.1 has no Qt6DBus and no Qt6LinguistTools modules (OHOS has no
  D-Bus / lrelease tools). Qt6LinguistTools is satisfied with a minimal stub
  so lxqt_translate_ts() becomes a no-op; the D-Bus code paths in
  application.cpp and the two qt6_add_dbus_adaptor() calls are dropped
  (single-instance service and org.freedesktop.FileManager1 are meaningless
  without a session bus).
- LayerShellQt is Wayland-only with no OHOS port; the desktop background
  layer code in desktopwindow.cpp and its CMake linkage are removed.
- X11-specific code in desktopwindow.cpp (EWMH via QNativeInterface::
  QX11Application) is removed — OHOS has no X11 and qtbase provides no
  QX11Application.
"""
import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeDeps, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file


class PcmanfmqtConan(ConanFile):
    name = "pcmanfm-qt"
    version = "2.4.0"
    description = "pcmanfm-qt 2.4.0"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/lxde/pcmanfm-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("lxqt2-build-tools/2.4.0", libs=False)
        self.requires("libfm-qt/2.4.0")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def _patch_file(self, path, old, new):
        replace_in_file(self, path, old, new)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

        # ---------- 1) drop LayerShellQt (Wayland-only) from root CMake ----------
        self._patch_file(
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "find_package(LayerShellQt ${SHELLQT_MINIMUM_VERSION} REQUIRED)\n",
            "")

        # ---------- 2) drop Qt6DBus from root CMake ----------
        self._patch_file(
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "find_package(Qt6DBus ${QT_MINIMUM_VERSION} REQUIRED)\n",
            "")

        # ---------- 3) pcmanfm/CMakeLists.txt: no dbus adaptors, no LayerShellQt ----------
        sub = os.path.join(self.source_folder, "pcmanfm", "CMakeLists.txt")
        dbus_adaptor_block = (
            "qt6_add_dbus_adaptor(pcmanfm_DBUS_SRCS\n"
            "    org.pcmanfm.Application.xml\n"
            "    application.h\n"
            "    PCManFM::Application\n"
            "    applicationadaptor\n"
            "    ApplicationAdaptor\n"
            ")\n"
            "\n"
            "qt6_add_dbus_adaptor(pcmanfm_DBUS_SRCS\n"
            "    org.freedesktop.FileManager1.xml\n"
            "    application.h\n"
            "    PCManFM::Application\n"
            "    applicationadaptorfreedesktopfilemanager\n"
            "    ApplicationAdaptorFreeDesktopFileManager\n"
            ")\n"
            "\n"
            "# qt6_add_dbus_adaptor() already generated the moc files. It also marked the\n"
            "# files with SKIP_AUTOMOC but we still need to mark them with SKIP_AUTOGEN.\n"
            "# TODO: Check if this behaviour is a CMake bug.\n"
            "set_source_files_properties(${pcmanfm_DBUS_SRCS} PROPERTIES SKIP_AUTOGEN ON)\n"
            "\n")
        if dbus_adaptor_block in open(sub).read():
            self._patch_file(sub, dbus_adaptor_block, "")
        # remove ${pcmanfm_DBUS_SRCS} from the executable target
        self._patch_file(
            sub,
            "add_executable(pcmanfm-qt\n"
            "    ${pcmanfm_SRCS}\n"
            "    ${pcmanfm_DBUS_SRCS}\n"
            "    ${pcmanfm_UIS}\n"
            "    ${QM_FILES}\n"
            "    ${DESKTOP_FILES}\n"
            ")",
            "add_executable(pcmanfm-qt\n"
            "    ${pcmanfm_SRCS}\n"
            "    ${pcmanfm_UIS}\n"
            "    ${QM_FILES}\n"
            "    ${DESKTOP_FILES}\n"
            ")")
        # drop Qt6::DBus and LayerShellQtInterface from link libraries
        self._patch_file(
            sub,
            "target_link_libraries(pcmanfm-qt\n"
            "    Qt6::Widgets\n"
            "    Qt6::DBus\n"
            "    LayerShellQtInterface\n"
            "    fm-qt6\n"
            ")",
            "target_link_libraries(pcmanfm-qt\n"
            "    Qt6::Widgets\n"
            "    fm-qt6\n"
            ")")

        # ---------- 4) application.cpp: remove DBus includes / adaptor refs ----------
        app = os.path.join(self.source_folder, "pcmanfm", "application.cpp")
        self._patch_file(
            app,
            "#include <QDBusConnection>\n"
            "#include <QDBusConnectionInterface>\n"
            "#include <QDBusInterface>\n",
            "")
        self._patch_file(
            app,
            "#include \"applicationadaptor.h\"\n"
            "#include \"applicationadaptorfreedesktopfilemanager.h\"\n",
            "")
        # X11/Xlib.h: the only use is an #if 0'ed nativeEventFilter; no X11
        # symbols are referenced anywhere else. Safe to drop on OHOS.
        self._patch_file(app, "#include <X11/Xlib.h>\n", "")
        # application.cpp uses QStandardPaths but never includes it directly
        # (previously resolved indirectly through a QtDBus header we removed).
        self._patch_file(
            app,
            "#include <QFileSystemWatcher>\n",
            "#include <QFileSystemWatcher>\n#include <QStandardPaths>\n")

        # Single-instance block: OHOS has no session bus, always primary.
        single_block = (
            "    // QDBusConnection::sessionBus().registerObject(\"/org/pcmanfm/Application\", this);\n"
            "    QDBusConnection dbus = QDBusConnection::sessionBus();\n"
            "    if(dbus.registerService(QLatin1String(serviceName))) {\n"
            "        // we successfully registered the service\n"
            "        isPrimaryInstance = true;\n"
            "        setStyle(new ProxyStyle());\n"
            "        //desktop()->installEventFilter(this);\n"
            "\n"
            "        new ApplicationAdaptor(this);\n"
            "        dbus.registerObject(QStringLiteral(\"/Application\"), this);\n"
            "\n"
            "        connect(this, &Application::aboutToQuit, this, &Application::onAboutToQuit);\n"
            "        // aboutToQuit() is not signalled on SIGTERM, install signal handler\n"
            "        installSigtermHandler();\n"
            "\n"
            "        // Check if LXQt Session is running. LXQt has it's own Desktop Folder\n"
            "        // editor. We just hide our editor when LXQt is running.\n"
            "        QDBusInterface* lxqtSessionIface = new QDBusInterface(\n"
            "            QStringLiteral(\"org.lxqt.session\"),\n"
            "            QStringLiteral(\"/LXQtSession\"));\n"
            "        if(lxqtSessionIface) {\n"
            "            if(lxqtSessionIface->isValid()) {\n"
            "                lxqtRunning_ = true;\n"
            "                userDesktopFolder_ = XdgDir::readDesktopDir();\n"
            "                initWatch();\n"
            "            }\n"
            "            delete lxqtSessionIface;\n"
            "            lxqtSessionIface = nullptr;\n"
            "        }\n"
            "\n"
            "\n"
            "        // We also try to register the service \"org.freedesktop.FileManager1\".\n"
            "        // We allow queuing of our request in case another file manager has already registered it.\n"
            "        static const QString fileManagerService = QStringLiteral(\"org.freedesktop.FileManager1\");\n"
            "        connect(dbus.interface(), &QDBusConnectionInterface::serviceRegistered, this, [this](const QString& service) {\n"
            "                if(fileManagerService == service) {\n"
            "                    QDBusConnection dbus = QDBusConnection::sessionBus();\n"
            "                    disconnect(dbus.interface(), &QDBusConnectionInterface::serviceRegistered, this, nullptr);\n"
            "                    new ApplicationAdaptorFreeDesktopFileManager(this);\n"
            "                    if(!dbus.registerObject(QStringLiteral(\"/org/freedesktop/FileManager1\"), this)) {\n"
            "                        qDebug() << \"Can't register /org/freedesktop/FileManager1:\" << dbus.lastError().message();\n"
            "                    }\n"
            "                }\n"
            "        });\n"
            "        dbus.interface()->registerService(fileManagerService, QDBusConnectionInterface::QueueService);\n"
            "    }\n"
            "    else {\n"
            "        // an service of the same name is already registered.\n"
            "        // we're not the first instance\n"
            "        isPrimaryInstance = false;\n"
            "    }\n")
        replacement = (
            "    // OHOS has no D-Bus session bus; always run as the primary instance.\n"
            "    isPrimaryInstance = true;\n"
            "    setStyle(new ProxyStyle());\n"
            "    connect(this, &Application::aboutToQuit, this, &Application::onAboutToQuit);\n"
            "    installSigtermHandler();\n")
        if single_block in open(app).read():
            self._patch_file(app, single_block, replacement)

        # Second-instance forwarding via D-Bus: no-op on OHOS (never reached).
        second_else = (
            "    else {\n"
            "        QDBusConnection dbus = QDBusConnection::sessionBus();\n"
            "        QDBusInterface iface(QLatin1String(serviceName), QStringLiteral(\"/Application\"), QLatin1String(ifaceName), dbus, this);\n"
            "        if(parser.isSet(quitOption)) {\n"
            "            iface.call(QStringLiteral(\"quit\"));\n"
            "            return false;\n"
            "        }\n"
            "\n"
            "        if(parser.isSet(desktopOption)) {\n"
            "            iface.call(QStringLiteral(\"desktopManager\"), true);\n"
            "        }\n"
            "        else if(parser.isSet(desktopOffOption)) {\n"
            "            iface.call(QStringLiteral(\"desktopManager\"), false);\n"
            "        }\n"
            "\n"
            "        if(parser.isSet(desktopPrefOption)) { // desktop preference dialog\n"
            "            iface.call(QStringLiteral(\"desktopPrefrences\"), parser.value(desktopPrefOption));\n"
            "        }\n"
            "        else if(parser.isSet(findFilesOption)) { // file searching utility\n"
            "            iface.call(QStringLiteral(\"findFiles\"), parser.positionalArguments());\n"
            "        }\n"
            "        else if(parser.isSet(showPrefOption)) { // preferences dialog\n"
            "            iface.call(QStringLiteral(\"preferences\"), parser.value(showPrefOption));\n"
            "        }\n"
            "        else if(parser.isSet(setWallpaperOption) || parser.isSet(wallpaperModeOption)) { // set wall paper\n"
            "            iface.call(QStringLiteral(\"setWallpaper\"), parser.value(setWallpaperOption), parser.value(wallpaperModeOption));\n"
            "        }\n"
            "        else {\n"
            "            if(!parser.isSet(desktopOption) && !parser.isSet(desktopOffOption)) {\n"
            "                bool reopenLastTabs = false;\n"
            "                QStringList paths = parser.positionalArguments();\n"
            "                if(paths.isEmpty()) {\n"
            "                    reopenLastTabs = true; // open last tab paths only if no path is specified\n"
            "                    paths.push_back(QDir::currentPath());\n"
            "                }\n"
            "                iface.call(QStringLiteral(\"launchFiles\"), QDir::currentPath(), paths, parser.isSet(newWindowOption), reopenLastTabs);\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    return keepRunning;\n")
        second_repl = (
            "    else {\n"
            "        // OHOS has no D-Bus; a second instance cannot hand off to the primary.\n"
            "        qWarning(\"Second pcmanfm-qt instance detected; D-Bus hand-off unavailable on OHOS.\");\n"
            "        return false;\n"
            "    }\n"
            "    return keepRunning;\n")
        if second_else in open(app).read():
            self._patch_file(app, second_else, second_repl)

        # ---------- 5) desktopwindow.cpp: drop X11 + LayerShellQt code ----------
        dw = os.path.join(self.source_folder, "pcmanfm", "desktopwindow.cpp")
        self._patch_file(
            dw,
            "#include <LayerShellQt/shell.h>\n"
            "#include <LayerShellQt/window.h>\n",
            "")
        # X11 include: still used elsewhere? only for EWMH block below; drop it.
        self._patch_file(dw, "#include <X11/Xlib.h>\n", "")
        # Wayland LayerShellQt block
        wayland_block = (
            "    // under Wayland, set the layer and anchors as well as window transparency\n"
            "    if(static_cast<Application*>(qApp)->underWayland()) {\n"
            "        setAttribute(Qt::WA_TranslucentBackground);\n"
            "        winId();\n"
            "        if(QWindow* win = windowHandle()) {\n"
            "            if(LayerShellQt::Window* layershell = LayerShellQt::Window::get(win)) {\n"
            "                layershell->setLayer(LayerShellQt::Window::Layer::LayerBackground);\n"
            "                LayerShellQt::Window::Anchors anchors = {LayerShellQt::Window::AnchorTop\n"
            "                                                         | LayerShellQt::Window::AnchorBottom\n"
            "                                                         | LayerShellQt::Window::AnchorLeft\n"
            "                                                         | LayerShellQt::Window::AnchorRight};\n"
            "                layershell->setAnchors(anchors);\n"
            "                layershell->setKeyboardInteractivity(LayerShellQt::Window::KeyboardInteractivityOnDemand);\n"
            "                layershell->setExclusiveZone(-1); // not moved to accommodate for other surfaces\n"
            "                layershell->setScope(QStringLiteral(\"desktop\")); // just for distinguishing it\n"
            "            }\n"
            "        }\n"
            "    }\n")
        if wayland_block in open(dw).read():
            self._patch_file(
                dw, wayland_block,
                "    // OHOS has no Wayland; desktop background layer is unavailable.\n")
        # X11 EWMH block QNativeInterface::QX11Application (no xcb in qtbase)
        x11_block = (
            "        if(QGuiApplication::platformName() == QStringLiteral(\"xcb\")) {\n"
            "            if(auto x11NativeInterfce = qApp->nativeInterface<QNativeInterface::QX11Application>()) {\n"
            "                xcb_connection_t* con = x11NativeInterfce->connection();\n"
            "                const char* atom_name = \"_NET_WM_WINDOW_TYPE_DESKTOP\";\n"
            "                xcb_atom_t atom = xcb_intern_atom_reply(con, xcb_intern_atom(con, 0, strlen(atom_name), atom_name), nullptr)->atom;\n"
            "                const char* prop_atom_name = \"_NET_WM_WINDOW_TYPE\";\n"
            "                xcb_atom_t prop_atom = xcb_intern_atom_reply(con, xcb_intern_atom(con, 0, strlen(prop_atom_name), prop_atom_name), nullptr)->atom;\n"
            "                xcb_atom_t XA_ATOM = 4;\n"
            "                xcb_change_property(con, XCB_PROP_MODE_REPLACE, effectiveWinId(), prop_atom, XA_ATOM, 32, 1, &atom);\n"
            "            }\n"
            "        }\n")
        if x11_block in open(dw).read():
            self._patch_file(dw, x11_block, "        // OHOS has no X11; EWMH window type is not set.\n")

        # ---------- 6) do not install autostart to /etc/xdg (no perm in conan) ----------
        au = os.path.join(self.source_folder, "autostart", "CMakeLists.txt")
        au_block = (
            "install(FILES\n"
            "    ${DESKTOP_FILES}\n"
            "    DESTINATION \"${LXQT_ETC_XDG_DIR}/autostart\"\n"
            "    COMPONENT Runtime\n"
            ")\n")
        if au_block in open(au).read():
            self._patch_file(
                au, au_block,
                "install(FILES\n"
                "    ${DESKTOP_FILES}\n"
                "    DESTINATION \"${CMAKE_INSTALL_DATADIR}/autostart\"\n"
                "    COMPONENT Runtime\n"
                ")\n")

    def generate(self):
        cmake_deps = CMakeDeps(self)
        if "qtbase" in self.dependencies.host:
            cmake_deps.set_property("qtbase", "cmake_find_mode", "none")
        cmake_deps.generate()
        tc = CMakeToolchain(self)
        if "libfm-qt" in self.dependencies.host:
            fm_dir = os.path.join(
                self.dependencies.host["libfm-qt"].package_folder,
                "share", "cmake", "fm-qt6",
            )
            if os.path.isdir(fm_dir):
                self._relocate_fm_qt6_targets(fm_dir)
                tc.variables["fm-qt6_DIR"] = fm_dir
        if "qtbase" in self.dependencies.host:
            qtbase_cmake = os.path.join(
                self.dependencies.host["qtbase"].package_folder,
                "lib", "cmake",
            )
            if os.path.isdir(qtbase_cmake):
                tc.variables["Qt6_DIR"] = os.path.join(qtbase_cmake, "Qt6")
                tc.variables["Qt6Widgets_DIR"] = os.path.join(qtbase_cmake, "Qt6Widgets")
                tc.variables["Qt6Gui_DIR"] = os.path.join(qtbase_cmake, "Qt6Gui")
                self._generate_linguisttools_stub(tc, qtbase_cmake)
        tc.generate()

    def _relocate_fm_qt6_targets(self, fm_dir):
        """Relocate absolute conan-cache paths baked into fm-qt6-targets.cmake.

        The libfm-qt package published to ohpcd was built on the CI worker,
        whose conan cache lives under .../.cache/conan2. Its exported
        fm-qt6-targets.cmake therefore hard-codes absolute include/library
        paths pointing into that worker cache (glib, menu-cache, libxcb,
        libexif, pcre2, zlib). Importing the fm-qt6 target fails on any other
        machine (e.g. a local ~/.conan2 cache) because those directories do
        not exist. Rewrite every ``/.../p/<pkg-hash>/p/...`` prefix to the
        current conan cache root so the imported target resolves everywhere.
        """
        targets = os.path.join(fm_dir, "fm-qt6-targets.cmake")
        if not os.path.isfile(targets):
            return
        cache_root = os.path.dirname(os.path.dirname(os.path.dirname(
            self.dependencies.host["libfm-qt"].package_folder)))
        with open(targets, encoding="utf-8") as f:
            content = f.read()
        pattern = re.compile(r"(/[^\";]*?)/p/([a-zA-Z0-9-]+)/p/")
        relocated, n = pattern.subn(
            lambda m: cache_root + "/p/" + m.group(2) + "/p/", content)
        if n:
            with open(targets, "w", encoding="utf-8") as f:
                f.write(relocated)
            self.output.info(
                f"relocated {n} conan-cache path(s) in fm-qt6-targets.cmake")

    def _generate_linguisttools_stub(self, tc, qtbase_cmake):
        stub_dir = os.path.join(self.generators_folder, "Qt6LinguistTools")
        os.makedirs(stub_dir, exist_ok=True)
        config = os.path.join(stub_dir, "Qt6LinguistToolsConfig.cmake")
        if not os.path.exists(config):
            with open(config, "w", encoding="utf-8") as f:
                f.write(
                    "set(Qt6LinguistTools_FOUND TRUE)\n"
                    "set(Qt6LinguistTools_VERSION 6.11.1)\n"
                    "if(NOT TARGET Qt6::lrelease)\n"
                    "  add_executable(Qt6::lrelease IMPORTED)\n"
                    "  set_target_properties(Qt6::lrelease PROPERTIES IMPORTED_LOCATION /bin/true)\n"
                    "endif()\n"
                    "if(NOT TARGET Qt6::lupdate)\n"
                    "  add_executable(Qt6::lupdate IMPORTED)\n"
                    "  set_target_properties(Qt6::lupdate PROPERTIES IMPORTED_LOCATION /bin/true)\n"
                    "endif()\n"
                    "function(qt6_add_translation _qm)\n"
                    "  set(${_qm} \"\" PARENT_SCOPE)\n"
                    "endfunction()\n"
                    "function(qt6_create_translation _qm)\n"
                    "  set(${_qm} \"\" PARENT_SCOPE)\n"
                    "endfunction()\n"
                )
        version = os.path.join(stub_dir, "Qt6LinguistToolsConfigVersion.cmake")
        if not os.path.exists(version):
            with open(version, "w", encoding="utf-8") as f:
                f.write(
                    "set(PACKAGE_VERSION 6.11.1)\n"
                    "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
                    "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
                    "else()\n"
                    "  set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                    "  if(PACKAGE_FIND_VERSION STREQUAL PACKAGE_VERSION)\n"
                    "    set(PACKAGE_VERSION_EXACT TRUE)\n"
                    "  endif()\n"
                    "endif()\n"
                )
        tc.variables["Qt6LinguistTools_DIR"] = stub_dir

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]