// kiconthemes 6.26.0 consumer test (R34: exercises real API).
// Verifies the KIconLoader singleton can be created and queried.
#include <KIconLoader>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KIconLoader *loader = KIconLoader::global();
    if (!loader) {
        std::printf("FAIL: KIconLoader::global() returned null\n");
        return 1;
    }
    std::printf("PASS: KIconLoader::global() OK\n");
    return 0;
}
