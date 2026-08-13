// karchive 6.14.0 consumer test (R34: exercises real API).
// Writes a zip archive via KZip and verifies the entry is listed back.
#include <KZip>
#include <QTemporaryFile>
#include <cstdio>

int main() {
    QTemporaryFile tmp;
    if (!tmp.open()) {
        std::printf("FAIL: cannot open temp file\n");
        return 1;
    }
    KZip zip(tmp.fileName());
    if (!zip.open(QIODevice::WriteOnly)) {
        std::printf("FAIL: cannot open zip for writing\n");
        return 1;
    }
    if (!zip.writeFile("hello.txt", "world")) {
        std::printf("FAIL: cannot write zip entry\n");
        return 1;
    }
    // close() returns false if data could not be fully flushed; without
    // this check the subsequent read may see truncated data.
    if (!zip.close()) {
        std::printf("FAIL: cannot close zip for writing\n");
        return 1;
    }

    KZip read(tmp.fileName());
    if (!read.open(QIODevice::ReadOnly)) {
        std::printf("FAIL: cannot reopen zip\n");
        return 1;
    }
    const KArchiveDirectory *dir = read.directory();
    if (!dir) {
        std::printf("FAIL: read.directory() returned null\n");
        return 1;
    }
    const KArchiveEntry *e = dir->entry("hello.txt");
    if (!e || !e->isFile()) {
        std::printf("FAIL: entry hello.txt not found\n");
        return 1;
    }
    std::printf("PASS: KZip write/read round-trip OK (%s)\n",
                qPrintable(e->name()));
    return 0;
}
