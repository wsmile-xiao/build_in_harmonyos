// kservice 6.26.0 consumer test (R34: exercises real API).
// Constructs a temporary KService and verifies desktop-service accessors.
#include <KService>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

static int fail(const char *message) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    KService service(QStringLiteral("OHOS Sample"),
                     QStringLiteral("sample-app --flag"),
                     QStringLiteral("sample-icon"));

    if (!service.isApplication()) {
        return fail("temporary service is not an application");
    }
    if (service.name() != QStringLiteral("OHOS Sample")) {
        return fail("service name did not round-trip");
    }
    if (service.exec() != QStringLiteral("sample-app --flag")) {
        return fail("service exec did not round-trip");
    }
    if (service.icon() != QStringLiteral("sample-icon")) {
        return fail("service icon did not round-trip");
    }

    std::printf("PASS: KService temporary service OK\n");
    return 0;
}
