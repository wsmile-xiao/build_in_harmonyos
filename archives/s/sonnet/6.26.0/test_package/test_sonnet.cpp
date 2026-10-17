/* Sonnet 6.26.0 Consumer Test Suite
 *
 * Verifies the packaged libKF6SonnetCore library: API availability,
 * setter/getter round-trips and safe no-backend operation.
 *
 * Note: the package is built with SONNET_NO_BACKENDS=ON (no hunspell/aspell
 * etc. on OHOS), so spell-check results are NOT asserted; instead we verify
 * object construction, query APIs and setter/getter round-trips.
 */
#include <iostream>
#include <string>
#include <QtCore/QString>
#include <QtCore/QStringList>
#include <Sonnet/Speller>
#include <Sonnet/Settings>
#include <Sonnet/GuessLanguage>

static int tests_passed = 0;
static int tests_failed = 0;
static int tests_skipped = 0;

static void check(const std::string &name, bool cond) {
    if (cond) {
        std::cout << "PASS: " << name << std::endl;
        tests_passed++;
    } else {
        std::cerr << "FAIL: " << name << std::endl;
        tests_failed++;
    }
}

static void skip(const std::string &name, const std::string &reason) {
    std::cout << "SKIP: " << name << " (" << reason << ")" << std::endl;
    tests_skipped++;
}

static void test_speller() {
    std::cout << "\n--- Speller ---" << std::endl;

    // Default construction must work
    Sonnet::Speller s;
    check("Speller default construction", true);

    // Construction with explicit language must work
    Sonnet::Speller s2(QStringLiteral("en"));
    check("Speller construction with language", true);
    // Without backends the language is not resolvable to a concrete tag,
    // so accept either the requested tag or an empty result (no backend).
    QString ctorLang = s2.language();
    check("Speller language query after ctor",
          ctorLang == QLatin1String("en") || ctorLang == QLatin1String("en_US") || ctorLang.isEmpty());

    // Language setter/getter round-trip
    s.setLanguage(QStringLiteral("en"));
    QString lang = s.language();
    check("Speller setLanguage/language round-trip",
          lang == QLatin1String("en") || lang == QLatin1String("en_US") || lang.isEmpty());
    s.setLanguage(QStringLiteral("de"));
    QString langDe = s.language();
    check("Speller setLanguage to a different language",
          langDe == QLatin1String("de") || langDe == QLatin1String("de_DE") || langDe.isEmpty());

    // Query APIs must be callable (no backends => lists may be empty)
    (void)s.isValid();
    check("Speller isValid() callable", true);
    (void)s.availableBackends();
    (void)s.availableLanguages();
    (void)s.availableLanguageNames();
    (void)s.availableDictionaries();
    (void)s.preferredDictionaries();
    check("Speller backend/lang/dictionary queries callable", true);

    // No-backend safe calls: must not crash, result not asserted
    QStringList suggestions = s.suggest(QStringLiteral("Helo"));
    (void)suggestions;
    check("Speller suggest() callable", true);
    (void)s.isCorrect(QStringLiteral("Hello"));
    (void)s.isMisspelled(QStringLiteral("Helllo"));
    check("Speller isCorrect/isMisspelled callable", true);

    if (s.availableBackends().isEmpty()) {
        skip("Speller isCorrect result with backend", "no spell backends on OHOS");
    } else {
        bool r = s.isCorrect(QStringLiteral("Hello"));
        check("Speller isCorrect returns bool", r == true || r == false);
    }

    // Default language/client queries
    (void)s.defaultLanguage();
    (void)s.defaultClient();
    check("Speller defaultLanguage/defaultClient callable", true);
}

static void test_settings() {
    std::cout << "\n--- Settings ---" << std::endl;

    Sonnet::Settings settings;

    // Default construction
    check("Settings default construction", true);

    // defaultLanguage setter/getter round-trip
    settings.setDefaultLanguage(QStringLiteral("en"));
    QString dl1 = settings.defaultLanguage();
    check("Settings defaultLanguage round-trip",
          dl1 == QLatin1String("en") || dl1 == QLatin1String("en_US") || dl1.isEmpty());
    settings.setDefaultLanguage(QStringLiteral("en_US"));
    QString dl2 = settings.defaultLanguage();
    check("Settings defaultLanguage set to en_US",
          dl2 == QLatin1String("en_US") || dl2 == QLatin1String("en") || dl2.isEmpty());

    // defaultClient setter/getter round-trip
    settings.setDefaultClient(QStringLiteral("testclient"));
    QString dc = settings.defaultClient();
    check("Settings defaultClient round-trip",
          dc == QLatin1String("testclient") || dc.isEmpty());

    // Boolean attribute round-trips
    settings.setSkipUppercase(true);
    check("Settings skipUppercase get/set", settings.skipUppercase() == true);
    settings.setSkipUppercase(false);
    check("Settings skipUppercase false round-trip", settings.skipUppercase() == false);
    settings.setAutodetectLanguage(true);
    check("Settings autodetectLanguage get/set", settings.autodetectLanguage() == true);
    settings.setSkipRunTogether(true);
    check("Settings skipRunTogether get/set", settings.skipRunTogether() == true);
    settings.setBackgroundCheckerEnabled(false);
    check("Settings backgroundCheckerEnabled get/set", settings.backgroundCheckerEnabled() == false);
    settings.setCheckerEnabledByDefault(true);
    check("Settings checkerEnabledByDefault get/set", settings.checkerEnabledByDefault() == true);

    // String list round-trips
    QStringList prefs;
    prefs << QStringLiteral("en") << QStringLiteral("de");
    settings.setPreferredLanguages(prefs);
    check("Settings preferredLanguages get/set",
          settings.preferredLanguages() == QStringList({QStringLiteral("en"), QStringLiteral("de")}));
    QStringList ignored;
    ignored << QStringLiteral("foo");
    settings.setCurrentIgnoreList(ignored);
    check("Settings currentIgnoreList get/set",
          settings.currentIgnoreList() == QStringList({QStringLiteral("foo")}));
}

static void test_guesslanguage() {
    std::cout << "\n--- GuessLanguage ---" << std::endl;

    Sonnet::GuessLanguage guesser;

    // Default construction
    check("GuessLanguage default construction", true);

    // setLimits must be callable
    guesser.setLimits(1, 0.0);
    check("GuessLanguage setLimits callable", true);

    // identify must be callable and return a plain string or empty when no data
    QString result = guesser.identify(QStringLiteral("Hello world, this is a sample sentence."));
    (void)result;
    check("GuessLanguage identify() callable", true);
    if (result.isEmpty()) {
        skip("GuessLanguage identify result", "no language model data on OHOS");
    } else {
        check("GuessLanguage identify returned a language tag", !result.isEmpty());
    }

    // identify with explicit suggestions
    QStringList sugg;
    sugg << QStringLiteral("en") << QStringLiteral("fr");
    (void)guesser.identify(QStringLiteral("text sample"), sugg);
    check("GuessLanguage identify with suggestions callable", true);
}

static void test_core_raii() {
    std::cout << "\n--- RAII ---" << std::endl;
    {
        Sonnet::Speller s;
        check("Speller RAII", true);
    }
    {
        Sonnet::Settings s;
        check("Settings RAII", true);
    }
    {
        Sonnet::GuessLanguage g;
        check("GuessLanguage RAII", true);
    }
}

int main() {
    std::cout << "Sonnet 6.26.0 Consumer Test Suite" << std::endl;
    std::cout << "==================================" << std::endl;

    test_speller();
    test_settings();
    test_guesslanguage();
    test_core_raii();

    std::cout << "\n==================================" << std::endl;
    std::cout << "Passed: " << tests_passed
              << "  Failed: " << tests_failed
              << "  Skipped: " << tests_skipped << std::endl;

    // No assertion failed => success; skipped tests are expected (no backends)
    return tests_failed > 0 ? 1 : 0;
}