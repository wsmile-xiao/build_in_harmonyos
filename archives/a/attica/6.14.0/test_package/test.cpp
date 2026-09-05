// attica 6.14.0 consumer test (R34: exercises real API).
// Verifies value-object accessors without relying on network I/O.
#include <Attica/Config>
#include <Attica/Person>
#include <QCoreApplication>
#include <QString>
#include <QUrl>
#include <cstdio>

static int fail(const char *message) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    Attica::Person person;
    person.setId(QStringLiteral("ada"));
    person.setFirstName(QStringLiteral("Ada"));
    person.setLastName(QStringLiteral("Lovelace"));
    person.setAvatarUrl(QUrl(QStringLiteral("https://example.invalid/avatar.png")));

    if (!person.isValid()) {
        return fail("person is not valid after id assignment");
    }
    if (person.firstName() != QStringLiteral("Ada")) {
        return fail("first name did not round-trip");
    }
    if (person.lastName() != QStringLiteral("Lovelace")) {
        return fail("last name did not round-trip");
    }
    if (person.avatarUrl().host() != QStringLiteral("example.invalid")) {
        return fail("avatar URL did not round-trip");
    }

    Attica::Config config;
    config.setHost(QStringLiteral("ocs.example.invalid"));
    config.setVersion(QStringLiteral("1.6"));
    config.setSsl(true);

    if (!config.isValid()) {
        return fail("config is not valid after host/version assignment");
    }
    if (config.version() != QStringLiteral("1.6")) {
        return fail("config version did not round-trip");
    }
    if (!config.ssl()) {
        return fail("config ssl flag did not round-trip");
    }

    std::printf("PASS: Attica value objects OK\n");
    return 0;
}
