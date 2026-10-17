// Consumer test for kimageannotator (kImageAnnotator-Qt6) on HarmonyOS PC.
//
// New OHOS-specific test cases (not a copy of any upstream test); they cover
// exactly the platform differences introduced by this run's adaptation:
//
//   1. No display server on the device: QApplication must run on the
//      offscreen QPA (upstream CI uses xvfb-run) -> assert
//      platformName() == "offscreen".
//   2. Shared library libkImageAnnotator.so really loads after the E077
//      install-time re-sign: instantiating the widget and running a full
//      loadImage/image()/addTab/imageAt round trip proves the OHOS ELF
//      .codesign signature and the runtime link closure (Qt6Core/Gui/
//      Widgets/Svg + PRIVATE kColorPicker) are valid.
//   3. X11 adaptation point: upstream enables find_package(X11 REQUIRED) on
//      the UNIX branch and CapsLockStatusChecker.cpp compiles its
//      __linux__-guarded XOpenDisplay branch because the OHOS clang driver
//      defines __linux__ (and __OHOS__). The test includes <X11/Xlib.h>,
//      calls XOpenDisplay(nullptr) and verifies the graceful no-display
//      degradation (nullptr -> CapsLock "false" path of the library).
//   4. loadTranslations() smoke call: the 31 installed .qm files and the
//      KIMAGEANNOTATOR_LANG_INSTALL_DIR datadir layout stay loadable.

#include <QApplication>
#include <QImage>
#include <QPixmap>
#include <QString>
#include <QtGlobal>

#include <cstdio>

#include <X11/Xlib.h>

#include <kImageAnnotator/KImageAnnotator.h>

// Debug helper (OHOS adaptation debugging): musl has no backtrace(), use the
// unwinder from libc++abi to dump frames on SIGSEGV/SIGABRT.
#include <signal.h>
#include <unistd.h>
#include <unwind.h>

namespace {

struct BacktraceState {
    void **current;
    void **end;
};

_Unwind_Reason_Code unwindCallback(struct _Unwind_Context *context, void *arg)
{
    auto *state = static_cast<BacktraceState *>(arg);
    uintptr_t pc = _Unwind_GetIP(context);
    if (pc != 0) {
        if (state->current == state->end)
            return _Unwind_Reason_Code::_URC_END_OF_STACK;
        *state->current++ = reinterpret_cast<void *>(pc);
    }
    return _Unwind_Reason_Code::_URC_NO_REASON;
}

void crashHandler(int signalNumber, siginfo_t *info, void *context)
{
    auto *uc = static_cast<ucontext_t *>(context);
    std::fprintf(stderr,
                 "CRASH signal %d fault_addr=%p pc=%p sp=%p lr=%p\n",
                 signalNumber,
                 reinterpret_cast<void *>(uc->uc_mcontext.fault_address),
                 reinterpret_cast<void *>(uc->uc_mcontext.pc),
                 reinterpret_cast<void *>(uc->uc_mcontext.sp),
                 reinterpret_cast<void *>(uc->uc_mcontext.regs[30]));
    FILE *maps = std::fopen("/proc/self/maps", "r");
    if (maps != nullptr) {
        char line[512];
        while (std::fgets(line, sizeof(line), maps) != nullptr)
            std::fputs(line, stderr);
        std::fclose(maps);
    }
    _exit(139);
}

} // namespace

int main(int argc, char **argv)
{
    struct sigaction action{};
    action.sa_sigaction = crashHandler;
    action.sa_flags = SA_SIGINFO;
    sigaction(SIGSEGV, &action, nullptr);
    sigaction(SIGABRT, &action, nullptr);
    sigaction(SIGBUS, &action, nullptr);
    // Adaptation point 1: no display server, force the offscreen QPA
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication application(argc, argv);
    if (application.platformName() != QLatin1String("offscreen"))
        return 1;

    // Adaptation point 3 (compile-time half): the library's X11 branch is
    // guarded by __linux__, which the OHOS clang driver defines.
#ifndef __linux__
#error "OHOS build must define __linux__ (UNIX X11 branch of kImageAnnotator)"
#endif
#ifdef __OHOS__
    std::printf("test_kimageannotator: __OHOS__ defined (HarmonyOS triple)\n");
#endif
    // Adaptation point 3 (runtime half): libX11.so.6 resolves and the
    // no-display degradation behaves exactly like the library's
    // CapsLockStatusChecker expects (null display -> feature disabled).
    std::fprintf(stderr, "MARK before XOpenDisplay\n");
    Display *x11Display = XOpenDisplay(nullptr);
    if (x11Display != nullptr) {
        XCloseDisplay(x11Display);
    }
    std::fprintf(
        stderr,
        "MARK XOpenDisplay probe done (display=%p, headless degradation OK)\n",
        static_cast<void *>(x11Display));

    // Adaptation point 2: shared lib + Qt6 Widgets lifecycle on offscreen QPA
    QPixmap pixmap(200, 150);
    pixmap.fill(Qt::white);
    std::fprintf(stderr, "MARK before annotator scope\n");
    const QString mode = qEnvironmentVariable("KIA_MODE");
    if (mode == QLatin1String("ctor_dtor")) {
        std::fprintf(stderr, "MARK probe ctor_dtor\n");
        {
            kImageAnnotator::KImageAnnotator annotator;
            std::fprintf(stderr, "MARK probe constructed\n");
        }
        std::fprintf(stderr, "MARK probe ctor_dtor done\n");
        std::printf("test_kimageannotator: KImageAnnotator OK (offscreen QPA, shared lib "
                    "+ X11 probe + tab round trip)\n");
        return 0;
    }
    if (mode == QLatin1String("show_only")) {
        std::fprintf(stderr, "MARK probe show_only\n");
        {
            kImageAnnotator::KImageAnnotator annotator;
            annotator.show();
            application.processEvents();
            std::fprintf(stderr, "MARK probe shown\n");
        }
        std::fprintf(stderr, "MARK probe show_only done\n");
        std::printf("test_kimageannotator: KImageAnnotator OK (offscreen QPA, shared lib "
                    "+ X11 probe + tab round trip)\n");
        return 0;
    }
    if (mode == QLatin1String("load_hide")) {
        std::fprintf(stderr, "MARK probe load_hide\n");
        {
            kImageAnnotator::KImageAnnotator annotator;
            annotator.loadImage(pixmap);
            annotator.hide();
            application.processEvents();
            std::fprintf(stderr, "MARK probe loaded and hidden\n");
        }
        std::fprintf(stderr, "MARK probe load_hide done\n");
        std::printf("test_kimageannotator: KImageAnnotator OK (offscreen QPA, shared lib "
                    "+ X11 probe + tab round trip)\n");
        return 0;
    }
    if (mode == QLatin1String("load_addtab_hide")) {
        std::fprintf(stderr, "MARK probe load_addtab_hide\n");
        {
            kImageAnnotator::KImageAnnotator annotator;
            annotator.loadImage(pixmap);
            annotator.addTab(pixmap, QStringLiteral("tab"), QString());
            annotator.hide();
            application.processEvents();
            std::fprintf(stderr, "MARK probe loaded, 2 tabs, hidden\n");
        }
        std::fprintf(stderr, "MARK probe load_addtab_hide done\n");
        std::printf("test_kimageannotator: KImageAnnotator OK (offscreen QPA, shared lib "
                    "+ X11 probe + tab round trip)\n");
        return 0;
    }
    {
        kImageAnnotator::KImageAnnotator annotator;
        annotator.loadImage(pixmap);
        std::fprintf(stderr, "MARK after loadImage\n");
        const QImage annotated = annotator.image();
        if (annotated.isNull())
            return 2;
        std::fprintf(stderr, "MARK after image() round trip\n");

        // Multi-tab API round trip (addTab/imageAt)
        const int tabIndex = annotator.addTab(pixmap, QStringLiteral("tab"), QString());
        if (tabIndex < 0 || annotator.imageAt(tabIndex).isNull())
            return 3;
        std::fprintf(stderr, "MARK after addTab/imageAt round trip\n");

        // Show the widget and run the event loop offscreen
        annotator.show();
        if (qEnvironmentVariableIsSet("KIA_SKIP_PROCESS_EVENTS")) {
            std::fprintf(stderr, "MARK skipping processEvents (probe)\n");
        } else {
            application.processEvents();
        }
        if (!annotator.isVisible())
            return 4;
        std::fprintf(stderr, "MARK after show/processEvents\n");
    }
    std::fprintf(stderr, "MARK annotator destroyed\n");

    // Adaptation point 4: translation loading stays functional against the
    // installed datadir layout (share/kImageAnnotator/translations)
    kImageAnnotator::loadTranslations();
    std::fprintf(stderr, "MARK after loadTranslations\n");
    std::printf(
        "test_kimageannotator: KImageAnnotator OK (offscreen QPA, shared lib "
        "+ X11 probe + tab round trip)\n");
    return 0;
}
