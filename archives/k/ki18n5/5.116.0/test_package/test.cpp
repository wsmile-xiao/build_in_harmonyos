// Consumer smoke test for ki18n5/5.116.0 on HarmonyOS PC.
// Exercises the real KLocalizedString API from libKF5I18n:
//   1. i18n() default-catalog formatting with a placeholder
//   2. KLocalizedString subs() chaining
//   3. KLocalizedString fallback when no catalog is loaded
#include <QCoreApplication>
#include <cstdio>

#include <KLocalizedString>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    int failures = 0;
    auto check = [&](bool ok, const char *what) {
        std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", what);
        if (!ok) {
            ++failures;
        }
    };

    // 1. i18n() returns a KLocalizedString; toString() formats it
    //    (untranslated pass-through when no catalog is loaded).
    KLocalizedString ks = ki18n("Hello %1");
    const QString s1 = ks.subs("world").toString();
    check(s1.contains(QLatin1String("world")), "i18n placeholder substitution");

    // 2. Chained subs() on a KLocalizedString.
    const QString s2 = ki18n("%1 and %2").subs("a").subs("b").toString();
    check(s2.contains(QLatin1String("a")) && s2.contains(QLatin1String("b")),
          "chained subs() formatting");

    // 3. The library is live: setApplicationDomain() round-trips through
    //    applicationDomain(). An empty domain is the documented default when
    //    the consumer never sets one, so we set our own and read it back.
    KLocalizedString::setApplicationDomain("test_ki18n5");
    const QByteArray domain = KLocalizedString::applicationDomain();
    check(domain == QByteArrayLiteral("test_ki18n5"),
          "application domain set/read-back");

    std::printf("test_ki18n5: %d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
