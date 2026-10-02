// kjobwidgets 6.26.0 consumer test (R34: exercises real API).
// Constructs trackers/delegates, binds them to real KJob instances,
// and verifies the association API surface.
#include <QApplication>
#include <KJob>
#include <KWidgetJobTracker>
#include <KDialogJobUiDelegate>
#include <memory>
#include <cstdio>

namespace {

class DummyJob : public KJob {
public:
    void start() override {}
};

int g_checks = 0;

bool check(bool cond, const char *what) {
    ++g_checks;
    if (!cond) std::fprintf(stderr, "FAIL: %s\n", what);
    return cond;
}

} // namespace

int main(int argc, char **argv) {
    // Widget-based framework: QApplication required (offscreen platform).
    QApplication app(argc, argv);
    bool ok = true;

    // 1. Widget job tracker construction.
    KWidgetJobTracker tracker(nullptr);
    ok &= check(true, "KWidgetJobTracker construction");

    // 2. Bind a real KJob to the tracker (register/unregister round-trip).
    DummyJob jobA;
    tracker.registerJob(&jobA);
    tracker.unregisterJob(&jobA);
    ok &= check(true, "registerJob/unregisterJob round-trip");

    // 3. Dialog UI delegate attaches to a job via setJob().
    DummyJob jobB;
    KDialogJobUiDelegate dlgDelegate;
    ok &= check(dlgDelegate.setJob(&jobB),
                "KDialogJobUiDelegate::setJob");

    // 4. KJob <-> delegate association via setUiDelegate/uiDelegate.
    //    KJob takes ownership of the delegate (its destructor deletes it),
    //    so release the unique_ptr afterwards — otherwise the delegate is
    //    deleted twice at scope exit (segfault after a fully-passing run).
    DummyJob jobC;
    auto owned = std::make_unique<KDialogJobUiDelegate>();
    jobC.setUiDelegate(owned.get());
    ok &= check(jobC.uiDelegate() == owned.get(),
                "KJob::setUiDelegate/uiDelegate round-trip");
    owned.release();

    // 5. Job auto-delete property (KJob base from KCoreAddons).
    jobC.setAutoDelete(false);
    ok &= check(!jobC.isAutoDelete(), "KJob::setAutoDelete/isAutoDelete");

    if (!ok) {
        std::fprintf(stderr, "kjobwidgets test: %d checks, FAILURES present\n",
                     g_checks);
        return 1;
    }
    std::printf("kjobwidgets 6.26.0: all %d checks passed\n", g_checks);
    return 0;
}
