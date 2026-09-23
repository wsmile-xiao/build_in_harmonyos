// baloo 6.28.0 consumer test (R34: exercises the installed public API).
// The engine (LMDB) layer is fully covered by the 37 upstream autotests run
// inside conan create (BUILD_TESTING=ON); this consumer test verifies that a
// downstream project can find KF6Baloo through CMake and exercise the public
// Query/QueryRunnable/IndexerConfig API surface without a running daemon.
#include <Baloo/Query>
#include <Baloo/QueryRunnable>
#include <Baloo/IndexerConfig>
#include <QString>
#include <QStringList>
#include <QJsonDocument>
#include <QTemporaryDir>
#include <QFile>
#include <cstdio>

using namespace Baloo;

int main() {
    // 1. Query API: build a query and round-trip it through JSON.
    Query query;
    query.addType(QStringLiteral("File"));
    query.setSearchString(QStringLiteral("hello AND world"));
    query.setLimit(10);
    query.setOffset(2);
    const QByteArray json = query.toJSON();
    if (json.isEmpty()) {
        std::printf("FAIL: query toJSON returned empty\n");
        return 1;
    }
    const QJsonDocument doc = QJsonDocument::fromJson(json);
    if (doc.isNull() || !doc.isObject()) {
        std::printf("FAIL: query toJSON is not a valid JSON object\n");
        return 1;
    }
    const Query parsed = Query::fromJSON(json);
    if (parsed.limit() != 10 || parsed.offset() != 2) {
        std::printf("FAIL: query JSON round-trip mismatch (limit=%d offset=%d)\n",
                    int(parsed.limit()), int(parsed.offset()));
        return 1;
    }
    if (!parsed.types().contains(QStringLiteral("File"))) {
        std::printf("FAIL: query JSON round-trip lost the type filter\n");
        return 1;
    }

    // 2. QueryRunnable: construct a runnable around the query (no daemon
    //    interaction happens at construction time).
    QueryRunnable runnable(parsed);
    Q_UNUSED(runnable);

    // 3. IndexerConfig: read/modify the local baloofilerc-style config
    //    (writes to the XDG config location, pure local file operations).
    QTemporaryDir dir;
    if (!dir.isValid()) {
        std::printf("FAIL: no temporary directory\n");
        return 1;
    }
    qputenv("XDG_CONFIG_HOME", dir.path().toUtf8());
    bool wasEnabled = false;
    bool persisted = false;
    {
        IndexerConfig config;
        wasEnabled = config.fileIndexingEnabled();
        config.setFileIndexingEnabled(!wasEnabled);
        // IndexerConfig persists in its destructor (m_settings.save()).
    }
    {
        IndexerConfig reread;
        persisted = (reread.fileIndexingEnabled() != wasEnabled);
    }
    if (!persisted) {
        std::printf("FAIL: IndexerConfig round-trip did not persist\n");
        return 1;
    }

    std::printf("PASS: Baloo Query JSON round-trip + QueryRunnable + "
                "IndexerConfig round-trip OK\n");
    return 0;
}
