// kbookmarks 6.14.0 consumer test (R34: exercises real API).
// Constructs a null KBookmark and verifies isNull() behaves as documented.
#include <KBookmark>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KBookmark bookmark;
    if (!bookmark.isNull()) {
        std::printf("FAIL: default-constructed KBookmark should be null\n");
        return 1;
    }
    std::printf("PASS: KBookmark default ctor isNull OK\n");
    return 0;
}
