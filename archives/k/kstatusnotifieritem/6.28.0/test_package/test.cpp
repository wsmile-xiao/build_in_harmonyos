#include <KStatusNotifierItem>

#include <QApplication>
#include <cstdio>

int main(int argc, char **argv)
{
    // Offscreen smoke test: exercise the public KStatusNotifierItem API
    // without DBus (USE_DBUS=OFF on the OHOS headless baseline, all DBus
    // code paths are compiled out via upstream #if HAVE_DBUS guards).
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication app(argc, argv);

    KStatusNotifierItem item(QStringLiteral("kteatime-smoke"));
    if (!item.id().endsWith(QStringLiteral("kteatime-smoke"))) {
        std::fprintf(stderr, "FAIL: id() mismatch\n");
        return 1;
    }
    if (item.status() != KStatusNotifierItem::Passive) {
        std::fprintf(stderr, "FAIL: default status is not Passive\n");
        return 1;
    }
    item.setTitle(QStringLiteral("HarmonyOS smoke"));
    item.setStatus(KStatusNotifierItem::Active);
    if (item.status() != KStatusNotifierItem::Active) {
        std::fprintf(stderr, "FAIL: setStatus(Active) not reflected\n");
        return 1;
    }
    item.setStatus(KStatusNotifierItem::Passive);
    if (item.status() != KStatusNotifierItem::Passive) {
        std::fprintf(stderr, "FAIL: setStatus(Passive) not reflected\n");
        return 1;
    }
    item.setCategory(KStatusNotifierItem::ApplicationStatus);
    item.setTitle(QStringLiteral("Smoke"));
    if (item.title() != QStringLiteral("Smoke")) {
        std::fprintf(stderr, "FAIL: setTitle not reflected\n");
        return 1;
    }
    std::printf("kstatusnotifieritem test_package: all assertions passed\n");
    return 0;
}
