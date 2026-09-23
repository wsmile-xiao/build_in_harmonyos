// karchive 6.26.0 consumer test (R34: exercises real API).
// Writes a gzip-compressed tar archive and reads the file back through KTar.
#include <KArchiveDirectory>
#include <KArchiveFile>
#include <KTar>
#include <QByteArray>
#include <QCoreApplication>
#include <QFileInfo>
#include <QIODevice>
#include <QTemporaryDir>
#include <cstdio>

static int fail(const char *message) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    QTemporaryDir dir;
    if (!dir.isValid()) {
        return fail("could not create temporary directory");
    }

    const QString archivePath = dir.filePath(QStringLiteral("payload.tar.gz"));
    const QByteArray payload("hello from karchive\n");

    {
        KTar tar(archivePath, QStringLiteral("application/gzip"));
        if (!tar.open(QIODevice::WriteOnly)) {
            return fail("could not open gzip tar for writing");
        }
        if (!tar.writeFile(QStringLiteral("docs/payload.txt"), payload)) {
            return fail("could not write file into archive");
        }
        if (!tar.close() || !QFileInfo::exists(archivePath)) {
            return fail("archive close/save failed");
        }
    }

    {
        KTar tar(archivePath, QStringLiteral("application/gzip"));
        if (!tar.open(QIODevice::ReadOnly)) {
            return fail("could not open gzip tar for reading");
        }
        const KArchiveDirectory *root = tar.directory();
        if (root == nullptr) {
            return fail("archive root directory is null");
        }
        const KArchiveFile *file = root->file(QStringLiteral("docs/payload.txt"));
        if (file == nullptr) {
            return fail("archive payload file was not found");
        }
        if (file->data() != payload) {
            return fail("archive payload did not round-trip");
        }
        if (!tar.close()) {
            return fail("archive close after read failed");
        }
    }

    std::printf("PASS: KTar gzip write/read OK\n");
    return 0;
}
