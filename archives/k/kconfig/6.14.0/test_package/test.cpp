// kconfig 6.14.0 consumer test (R34: exercises real API).
// Creates an in-memory KConfig and verifies KConfigGroup round-trip.
#include <KConfig>
#include <KConfigGroup>
#include <QString>
#include <cstdio>

int main() {
    KConfig config(QStringLiteral("testconfig"), KConfig::SimpleConfig);
    KConfigGroup grp = config.group(QStringLiteral("General"));
    grp.writeEntry(QStringLiteral("name"), QStringLiteral("world"));
    config.sync();
    KConfig reread(QStringLiteral("testconfig"), KConfig::SimpleConfig);
    const QString v =
        reread.group(QStringLiteral("General")).readEntry("name", QString());
    if (v != QStringLiteral("world")) {
        std::printf("FAIL: config round-trip mismatch: %s\n",
                    v.toUtf8().constData());
        return 1;
    }
    std::printf("PASS: KConfig group round-trip OK (name=%s)\n",
                v.toUtf8().constData());
    return 0;
}
