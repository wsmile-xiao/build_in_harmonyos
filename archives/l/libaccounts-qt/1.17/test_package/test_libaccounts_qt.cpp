/*
 * Consumer-side smoke test for libaccounts-qt 1.17 (AccountsQt6).
 *
 * Exercises real public API of the packaged library:
 *   - Accounts::Error (in-memory, no D-Bus required) with hard assertions
 *   - Accounts::Manager construction, which binds to libaccounts-glib and
 *     proves the shared/static library plus its dependency chain link.
 */
#include <Accounts/Account>
#include <Accounts/Error>
#include <Accounts/Manager>

#include <QCoreApplication>
#include <QDebug>
#include <QString>

#include <cstdio>

static int failures = 0;

static void check(bool ok, const char *what)
{
    if (!ok) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        ++failures;
    } else {
        std::printf("PASS: %s\n", what);
    }
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1) Accounts::Error round-trip (pure in-process API).
    Accounts::Error err(Accounts::Error::DatabaseLocked, QStringLiteral("smoke-test"));
    check(err.type() == Accounts::Error::DatabaseLocked, "Error::type round-trip");
    check(err.message() == QStringLiteral("smoke-test"), "Error::message round-trip");

    Accounts::Error copy(err);
    check(copy.type() == Accounts::Error::DatabaseLocked, "Error copy ctor keeps type");
    check(err.type() == Accounts::Error::DatabaseLocked, "Error copy source unchanged");

    Accounts::Error empty;
    check(empty.type() == Accounts::Error::NoError, "default Error is NoError");

    // 2) Accounts::Manager: constructing it resolves symbols from
    //    libaccounts-glib (and through it glib/gio), i.e. link + runtime
    //    dependency chain of the package are complete.
    Accounts::Manager manager;
    check(true, "Accounts::Manager constructed (libaccounts-glib bound)");

    std::printf("AccountsQt6 API checks done, failures=%d\n", failures);
    if (failures == 0) {
        std::printf("libaccounts-qt 1.17 smoke test PASSED\n");
    }
    return failures == 0 ? 0 : 1;
}
