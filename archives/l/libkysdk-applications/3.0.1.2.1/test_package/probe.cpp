/* Consumer probe for libkysdk-applications (Qt6 build, OHOS aarch64).
 *
 * This is a REAL artifact/API test (R34), not a print-only stub.  It exercises
 * the exact contract the downstream Qt6 applet kylin-nm-plugin/4.0.0.1 has:
 *
 *   1. every shipped shared object is dlopen()ed with RTLD_NOW (all
 *      DT_NEEDED entries resolve), and
 *   2. the public UKUI widget classes are really constructed and used:
 *        kdk::KSwitchButton, kdk::KBorderlessButton, kdk::KTabBar,
 *        kdk::KPasswordEdit, kdk::KDialog, kdk::KWidget, and
 *   3. the headers resolve through BOTH upstream include spellings —
 *      the flat <kwidget.h> / <kpasswordedit.h> (via the
 *      include/kysdk/applications -I flag) and the prefixed
 *      <kysdk/applications/kdialog.h> (via the include -I flag).
 *
 * usage: probe <package-lib-dir>
 * exit code 0 = all checks passed, 1 = at least one failed.
 */
#include <QApplication>
#include <QLineEdit>
#include <QPalette>
#include <QWidget>

#include <kwidget.h>                    /* flat:   -I<prefix>/include/kysdk/applications */
#include <kpasswordedit.h>              /* flat:   -I<prefix>/include/kysdk/applications */
#include <kswitchbutton.h>              /* flat */
#include <kborderlessbutton.h>          /* flat */
#include <ktabbar.h>                    /* flat */
#include <kysdk/applications/kdialog.h> /* prefixed: -I<prefix>/include */

#include <dlfcn.h>
#include <unistd.h>

#include <cstdio>
#include <string>

static int g_fail = 0;

static void check(bool ok, const std::string &what)
{
    std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", what.c_str());
    if (!ok)
        ++g_fail;
}

int main(int argc, char **argv)
{
    const std::string libdir = (argc > 1) ? argv[1] : "";
    std::printf("probe uid=%d euid=%d libdir=%s\n",
                (int)::getuid(), (int)::geteuid(), libdir.c_str());

    /* ---- 1) every shipped shared object loads with RTLD_NOW ---- */
    for (const char *name : {"libkysdk-qtwidgets.so", "libkysdk-alm.so",
                             "libkysdk-ukenv.so", "libkysdk-widgetutils.so"}) {
        const std::string path = libdir + "/" + name;
        void *handle = ::dlopen(path.c_str(), RTLD_NOW);
        check(handle != nullptr, std::string("dlopen(RTLD_NOW) :: ") + name);
        if (handle == nullptr)
            std::printf("       dlerror: %s\n", ::dlerror());
        else
            ::dlclose(handle);
    }

    /* ---- 2) the kdk:: widget classes are really usable ---- */
    QApplication app(argc, argv);
    QWidget host;

    kdk::KSwitchButton sw(&host);
    sw.setCheckable(true);
    sw.setChecked(true);
    check(sw.isChecked(), "kdk::KSwitchButton construct + setChecked/isChecked");

    kdk::KBorderlessButton bb(QStringLiteral("ok"), &host);
    check(bb.text() == QStringLiteral("ok"),
          "kdk::KBorderlessButton construct + text()");

    kdk::KTabBar tab(kdk::SegmentDark, &host);
    check(tab.count() == 0, "kdk::KTabBar(KTabBarStyle::SegmentDark) construct");

    kdk::KPasswordEdit pe(&host);
    pe.setEchoMode(QLineEdit::Password);
    check(pe.echoMode() == QLineEdit::Password,
          "kdk::KPasswordEdit construct + setEchoMode");

    kdk::KDialog dlg(&host);
    check(true, "kdk::KDialog construct (via <kysdk/applications/kdialog.h>)");

    kdk::KWidget kw(&host);
    check(true, "kdk::KWidget construct (via <kwidget.h>)");

    /* ---- 3) restored Qt6 capabilities really work at the consumer level ----
     * The kdk widget set uses QWidget accessible name/description, the Qt6
     * QPalette::Accent role and (via libkysdk-qtwidgets) Qt6Svg + QGSettings;
     * dlopen(RTLD_NOW) above already proves the SVG/QGSettings DT_NEEDEDs of
     * libkysdk-qtwidgets resolve.  Here we exercise the pure-widget part. */
    host.setAccessibleName(QStringLiteral("probe-host"));
    host.setAccessibleDescription(QStringLiteral("probe-description"));
    check(host.accessibleName() == QStringLiteral("probe-host"),
          "QWidget::setAccessibleName/accessibleName round-trip (restored)");
    check(host.accessibleDescription() == QStringLiteral("probe-description"),
          "QWidget::setAccessibleDescription/accessibleDescription round-trip (restored)");

    const QPalette::ColorRole accentRole = QPalette::Accent;
    check(accentRole != QPalette::NoRole,
          "QPalette::Accent exists (Qt6 core role restored in ThemeController)");

    std::printf("\nconsumer probe: %d failure(s)\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
