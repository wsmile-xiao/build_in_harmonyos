// kservice 6.14.0 consumer test (R34: exercises real API).
#include <kservice.h>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    // KService::serviceByDesktopPath returns a null Ptr for unknown paths,
    // which still proves the API links and is callable.
    KService::Ptr svc =
        KService::serviceByDesktopPath(QStringLiteral("nonexistent.desktop"));
    std::printf("PASS: KService::serviceByDesktopPath OK (null=%d)\n",
                svc.data() == nullptr);
    return 0;
}
