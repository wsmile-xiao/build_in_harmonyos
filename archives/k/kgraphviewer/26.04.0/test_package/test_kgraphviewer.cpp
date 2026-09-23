// Consumer test for kgraphviewer 26.04.0 on HarmonyOS PC.
//
// Upstream ships no tests (NO_UPSTREAM_TESTS — see manifest.yaml); this
// test exercises the installed package as a real consumer, offscreen:
//   1. the kgraphviewerpart KParts plugin loads and is a KParts::ReadOnlyPart
//      (proves the vendored libKF6Parts.so.6 ABI + the whole link closure);
//   2. opening a local .dot file completes (KParts completed signal), which
//      for the default InternalLibrary layout method runs the full
//      in-process parse + graphviz layout pipeline;
//   3. the graphviz C API is driven directly (cgraph agread, gvc dot
//      layout, plain render) to prove the plugin config lookup (GVBINDIR)
//      and the FindGraphviz bridge link closure.
#include <cstdio>
#include <cstring>
#include <cstdlib>

#include <QApplication>
#include <QEventLoop>
#include <QFile>
#include <QStandardPaths>
#include <QTimer>
#include <QUrl>
#include <QPluginLoader>

#include <KParts/ReadOnlyPart>
#include <KPluginFactory>

#include <graphviz/gvc.h>
#include <graphviz/cgraph.h>

static int failures = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (cond) {                                                          \
            std::printf("PASS: %s\n", msg);                                  \
            std::fflush(stdout);                                             \
        } else {                                                             \
            std::printf("FAIL: %s\n", msg);                                  \
            std::fflush(stdout);                                             \
            ++failures;                                                      \
        }                                                                    \
    } while (0)

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    // ── 1. write a small .dot file ──
    const QString dir = QStandardPaths::writableLocation(
        QStandardPaths::TempLocation);
    const QString dotPath = dir + QStringLiteral("/kgraphviewer_ohos_smoke.dot");
    {
        QFile f(dotPath);
        if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
            std::printf("FAIL: cannot write temp dot file\n");
            return 2;
        }
        f.write("digraph ohos_smoke { rankdir=LR; ohos_src -> kgraphviewer; "
                "kgraphviewer -> graphviz; }\n");
    }

    // ── 2. load the installed KParts plugin ──
    const QString partPath = qEnvironmentVariable("KGV_PART_PLUGIN");
    CHECK(!partPath.isEmpty(), "KGV_PART_PLUGIN env var is set");
    QPluginLoader loader(partPath);
    QObject *root = loader.instance();
    if (!root) {
        std::printf("plugin error: %s\n", qPrintable(loader.errorString()));
        std::fflush(stdout);
    }
    CHECK(root != nullptr, "kgraphviewerpart plugin instance() loads");
    // The plugin root object is a KPluginFactory; the part is created
    // through it (standard KParts plugin layout).
    auto *factory = qobject_cast<KPluginFactory *>(root);
    CHECK(factory != nullptr, "plugin exposes a KPluginFactory");
    if (!factory) {
        return 1;
    }
    auto *part = factory->create<KParts::ReadOnlyPart>();
    CHECK(part != nullptr, "part is a KParts::ReadOnlyPart (vendored KParts ABI)");
    if (!part) {
        return 1;
    }

    // ── 3. open the dot file; completed() fires after openFile() returned
    // true, and openFile() runs loadLibrarySync() (in-process graphviz
    // layout) for the default InternalLibrary method ──
    bool done = false;
    bool completed = false;
    QString cancelReason;
    QEventLoop loop;
    QTimer::singleShot(120000, &loop, &QEventLoop::quit);
    QObject::connect(part, &KParts::ReadOnlyPart::completed, &loop,
                     [&]() { done = true; completed = true; loop.quit(); });
    QObject::connect(part, &KParts::ReadOnlyPart::canceled, &loop,
                     [&](const QString &msg) {
                         done = true;
                         cancelReason = msg;
                         loop.quit();
                     });
    part->openUrl(QUrl::fromLocalFile(dotPath));
    loop.exec();
    CHECK(done, "part loading finished within the timeout");
    if (!cancelReason.isEmpty()) {
        std::printf("canceled reason: %s\n", qPrintable(cancelReason));
        std::fflush(stdout);
    }
    CHECK(completed, "part completed full DOT parse + layout (in-process)");

    // ── 4. drive the graphviz C API directly ──
    GVC_t *gvc = gvContext();
    CHECK(gvc != nullptr, "gvContext() (graphviz closure + plugin config)");
    FILE *fp = fopen(dotPath.toUtf8().constData(), "r");
    graph_t *g = fp ? agread(fp, nullptr) : nullptr;
    if (fp) {
        fclose(fp);
    }
    CHECK(g != nullptr, "cgraph agread() parses the dot file");
    if (g) {
        const int lrc = gvLayout(gvc, g, const_cast<char *>("dot"));
        CHECK(lrc == 0, "gvLayout dot engine runs in-process (GVBINDIR config)");
        char *data = nullptr;
        size_t len = 0;
        const int rrc = gvRenderData(gvc, g, const_cast<char *>("plain"),
                                     &data, &len);
        CHECK(rrc == 0 && data && std::strstr(data, "ohos_src") != nullptr,
              "gvRenderData plain output contains the source node");
        if (data) {
            gvFreeRenderData(data);
        }
        if (lrc == 0) {
            gvFreeLayout(gvc, g);
        }
        agclose(g);
    }
    if (gvc) {
        gvFreeContext(gvc);
    }

    if (failures == 0) {
        std::printf("test_kgraphviewer: all checks passed\n");
        return 0;
    }
    std::printf("test_kgraphviewer: %d check(s) FAILED\n", failures);
    return 1;
}
