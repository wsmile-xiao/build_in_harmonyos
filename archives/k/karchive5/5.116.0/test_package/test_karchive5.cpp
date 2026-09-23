// Smoke test for the karchive5 (KDE Frameworks 5) Conan package on OHOS.
//
// It exercises the real public KF5Archive API end to end:
//   1. KZip::open(QIODevice::WriteOnly)  -> write entries
//   2. KArchiveDirectory::addEntry       -> build the in-archive tree
//   3. KZip::close                       -> finalise the archive
//   4. KZip::open(QIODevice::ReadOnly)   -> reopen the produced file
//   5. KArchive::directory()             -> walk the entry tree
//   6. KArchiveFile::data()              -> read the payload back
//   7. KCompressionDevice                 -> gzip filter round trip
//
// Any failure prints a diagnostic and returns a non-zero exit code so CTest
// reports it.
#include <QBuffer>
#include <QByteArray>
#include <QIODevice>
#include <QString>
#include <QStringList>

#include <cstdio>

#include <karchive.h>
#include <karchive_version.h>
#include <karchivedirectory.h>
#include <karchiveentry.h>
#include <karchivefile.h>
#include <kcompressiondevice.h>
#include <kzip.h>

namespace {

int g_failures = 0;

void check(bool condition, const char *what)
{
    if (condition) {
        std::printf("PASS: %s\n", what);
    } else {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    }
}

// Build a ZIP archive in memory and return its bytes.
QByteArray buildZip()
{
    QBuffer buffer;
    buffer.open(QIODevice::WriteOnly);

    KZip zip(&buffer);
    check(zip.open(QIODevice::WriteOnly), "KZip::open(WriteOnly)");

    check(zip.writeFile(QStringLiteral("docs/readme.txt"),
                        QByteArray("karchive5 smoke payload")),
          "KZip::writeFile(docs/readme.txt)");
    check(zip.writeFile(QStringLiteral("docs/nested/data.bin"),
                        QByteArray("nested payload")),
          "KZip::writeFile(docs/nested/data.bin)");

    check(zip.close(), "KZip::close()");
    return buffer.data();
}

void readZipBack(const QByteArray &bytes)
{
    QBuffer buffer;
    buffer.setData(bytes);
    buffer.open(QIODevice::ReadOnly);

    KZip zip(&buffer);
    check(zip.open(QIODevice::ReadOnly), "KZip::open(ReadOnly)");

    const KArchiveDirectory *root = zip.directory();
    check(root != nullptr, "KArchive::directory() returns the root entry");

    if (!root) {
        return;
    }

    const KArchiveEntry *docsEntry = root->entry(QStringLiteral("docs"));
    check(docsEntry != nullptr, "root entry 'docs' is present");
    check(docsEntry && docsEntry->isDirectory(), "'docs' is a directory");

    const auto *docs = dynamic_cast<const KArchiveDirectory *>(docsEntry);
    check(docs != nullptr, "'docs' downcasts to KArchiveDirectory");
    if (!docs) {
        return;
    }

    const QStringList entries = docs->entries();
    check(entries.contains(QStringLiteral("readme.txt")),
          "docs/readme.txt listed in the archive tree");
    check(entries.contains(QStringLiteral("nested")),
          "docs/nested listed in the archive tree");

    const KArchiveFile *readme =
        dynamic_cast<const KArchiveFile *>(docs->entry(QStringLiteral("readme.txt")));
    check(readme != nullptr, "docs/readme.txt is a KArchiveFile");
    if (readme) {
        const QByteArray data = readme->data();
        check(data == QByteArray("karchive5 smoke payload"),
              "docs/readme.txt payload round trips byte for byte");
        std::printf("INFO: docs/readme.txt size=%d\n", int(data.size()));
    }

    const auto *nested = dynamic_cast<const KArchiveDirectory *>(
        docs->entry(QStringLiteral("nested")));
    check(nested != nullptr, "docs/nested is a KArchiveDirectory");
    if (nested) {
        const KArchiveFile *bin = dynamic_cast<const KArchiveFile *>(
            nested->entry(QStringLiteral("data.bin")));
        check(bin != nullptr, "docs/nested/data.bin is a KArchiveFile");
        if (bin) {
            check(bin->data() == QByteArray("nested payload"),
                  "docs/nested/data.bin payload round trips byte for byte");
        }
    }
}

// KCompressionDevice with the GZip filter is what KTar relies on; drive it
// through a memory device to prove the compression backend is functional.
void compressionRoundTrip()
{
    const QByteArray payload("karchive5 compression filter payload");

    QBuffer compressed;
    compressed.open(QIODevice::WriteOnly);
    {
        KCompressionDevice device(&compressed, false, KCompressionDevice::GZip);
        check(device.open(QIODevice::WriteOnly),
              "KCompressionDevice::open(WriteOnly, GZip)");
        const qint64 written = device.write(payload);
        check(written == payload.size(), "KCompressionDevice::write() wrote all bytes");
        device.close();
    }

    const QByteArray compressedBytes = compressed.data();
    check(!compressedBytes.isEmpty(), "gzip stream is non-empty");
    check(compressedBytes != payload,
          "gzip stream is actually compressed (differs from input)");

    QBuffer source;
    source.setData(compressedBytes);
    source.open(QIODevice::ReadOnly);
    KCompressionDevice reader(&source, false, KCompressionDevice::GZip);
    check(reader.open(QIODevice::ReadOnly),
          "KCompressionDevice::open(ReadOnly, GZip)");
    const QByteArray restored = reader.readAll();
    check(restored == payload, "gzip round trip restores the payload");
}

// bzip2 / xz / zstd backends are only compiled in when the corresponding
// dependency was found; probe them through the same public filter API.
void probeOptionalFilters()
{
    const struct {
        const char *name;
        KCompressionDevice::CompressionType type;
    } filters[] = {
        {"BZip2", KCompressionDevice::BZip2},
        {"Xz", KCompressionDevice::Xz},
        {"Zstd", KCompressionDevice::Zstd},
    };

    for (const auto &filter : filters) {
        QBuffer sink;
        sink.open(QIODevice::WriteOnly);
        KCompressionDevice device(&sink, false, filter.type);
        if (!device.open(QIODevice::WriteOnly)) {
            std::printf("INFO: %s filter not available in this build\n", filter.name);
            continue;
        }
        const QByteArray payload("optional backend payload");
        device.write(payload);
        device.close();
        std::printf("INFO: %s filter wrote %d bytes\n",
                    filter.name, int(sink.data().size()));
        check(!sink.data().isEmpty(),
              qPrintable(QStringLiteral("%1 filter produced output").arg(filter.name)));
    }
}

} // namespace

int main()
{
    std::printf("karchive5 smoke test (KF5Archive %s)\n", KARCHIVE_VERSION_STRING);

    const QByteArray archive = buildZip();
    check(!archive.isEmpty(), "ZIP archive was produced");
    std::printf("INFO: archive size=%d bytes\n", int(archive.size()));

    readZipBack(archive);
    compressionRoundTrip();
    probeOptionalFilters();

    if (g_failures == 0) {
        std::printf("ALL CHECKS PASSED\n");
        return 0;
    }
    std::printf("%d CHECK(S) FAILED\n", g_failures);
    return 1;
}
