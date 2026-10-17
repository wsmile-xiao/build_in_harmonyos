// libkmahjongg 26.04.0 consumer test (R34: exercises real API).
// Constructs a KMahjonggTileset, loads the default tileset via
// loadDefault() and verifies the load actually succeeded — a failed
// load (e.g. missing tileset data files or broken packaging) must
// make the test fail with a non-zero exit code.
#include <KMahjonggTileset>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KMahjonggTileset tileset;
    if (!tileset.loadDefault()) {
        std::fprintf(stderr, "FAIL: KMahjonggTileset could not load default tileset\n");
        return 1;
    }
    std::printf("PASS: KMahjonggTileset default tileset loaded OK (name: %s)\n",
                qPrintable(tileset.name()));
    return 0;
}
