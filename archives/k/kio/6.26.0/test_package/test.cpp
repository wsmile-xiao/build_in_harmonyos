// kio 6.26.0 consumer test (R34: exercises real KIOCore APIs).
// Uses pure in-library KIOCore APIs that do not spawn a kioworker
// subprocess over D-Bus (no session bus on the OHOS build host, so
// worker-based jobs like KIO::stat cannot run; the same shape as the
// 6.18.0 consumer test, upgraded for the 6.26.0 baseline).
#include <KIO/Global>
#include <KFileItem>
#include <KFileFilter>
#include <QCoreApplication>
#include <QMimeDatabase>
#include <QUrl>
#include <cstdio>

static int fail(const char *message) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    // 1. KFileItem round-trip (KIOCore data model).
    const QUrl url(QStringLiteral("file:///nonexistent/kio-test"));
    KFileItem item(url);
    if (!item.isNull() && item.name().isEmpty()) {
        return fail("KFileItem name is empty for a non-null item");
    }
    std::printf("PASS: KFileItem constructed, name=%s\n",
                qPrintable(item.name()));

    // 2. KIO::convertSize pure utility.
    const QString size = KIO::convertSize(1024);
    if (size.isEmpty()) {
        return fail("KIO::convertSize returned an empty string");
    }
    std::printf("PASS: KIO::convertSize(1024) = %s\n", qPrintable(size));

    // 3. KFileFilter (KIOCore since 5.101): 6.26.0 replaced the old
    // setName/addMimeType setters with value-style construction
    // (label, filePatterns, mimePatterns ctor + fromMimeType factory);
    // use those APIs for the validity round-trip.
    const KFileFilter filter = KFileFilter::fromMimeType(
        QStringLiteral("text/plain"));
    if (!filter.isValid()) {
        return fail("KFileFilter::fromMimeType(text/plain) is not valid");
    }
    const KFileFilter namedFilter(
        QStringLiteral("Text files"),
        QStringList() << QStringLiteral("*.txt"),
        QStringList());
    if (namedFilter.filePatterns() != QStringList(QStringLiteral("*.txt"))) {
        return fail("KFileFilter filePatterns round-trip mismatch");
    }
    if (!namedFilter.toFilterString().contains(QStringLiteral("*.txt"))) {
        return fail("KFileFilter toFilterString does not contain the pattern");
    }
    const KFileFilter mimeFilter(
        QString(),
        QStringList(),
        QStringList() << QStringLiteral("text/plain"));
    if (!mimeFilter.mimePatterns().contains(QStringLiteral("text/plain"))) {
        return fail("KFileFilter mimePatterns round-trip mismatch");
    }
    std::printf("PASS: KFileFilter valid, filterString=%s\n",
                qPrintable(namedFilter.toFilterString()));

    // 4. KIO::iconNameForUrl pure helper.
    const QString iconName = KIO::iconNameForUrl(QUrl(
        QStringLiteral("file:///nonexistent/kio-test")));
    if (iconName.isEmpty()) {
        return fail("KIO::iconNameForUrl returned an empty icon name");
    }
    std::printf("PASS: KIO::iconNameForUrl = %s\n", qPrintable(iconName));

    std::printf("PASS: kio 6.26.0 KIOCore consumer test OK\n");
    return 0;
}
