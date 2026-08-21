// kbookmarks 6.18.0 consumer test (R34: exercises real API).
// Creates a bookmark file, adds a bookmark, saves it, and looks it up again.
#include <KBookmark>
#include <KBookmarkManager>
#include <QCoreApplication>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QUrl>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    QTemporaryDir dir;
    if (!dir.isValid()) {
        std::fprintf(stderr, "FAIL: could not create temporary directory\n");
        return 1;
    }

    const QString bookmarkFile = dir.filePath(QStringLiteral("bookmarks.xml"));
    KBookmarkManager manager(bookmarkFile);

    KBookmarkGroup root = manager.root();
    const QUrl url(QStringLiteral("https://example.org/kbookmarks"));
    KBookmark bookmark = root.addBookmark(QStringLiteral("Example"), url, QString());
    if (bookmark.isNull() || bookmark.url() != url) {
        std::fprintf(stderr, "FAIL: bookmark was not added with the expected URL\n");
        return 1;
    }
    if (!manager.saveAs(bookmarkFile, false) || !QFileInfo::exists(bookmarkFile)) {
        std::fprintf(stderr, "FAIL: bookmark file was not saved\n");
        return 1;
    }

    KBookmark found = manager.findByAddress(bookmark.address());
    if (found.isNull() || found.text() != QStringLiteral("Example")) {
        std::fprintf(stderr, "FAIL: bookmark lookup by address failed\n");
        return 1;
    }

    std::printf("PASS: KBookmarkManager add/save/find OK\n");
    return 0;
}
