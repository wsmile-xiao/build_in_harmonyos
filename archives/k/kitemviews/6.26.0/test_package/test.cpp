// kitemviews 6.26.0 consumer test (R34: exercises real API).
// Constructs a KTreeWidgetSearchLine and verifies basic behavior.
#include <KTreeWidgetSearchLine>
#include <QApplication>
#include <QTreeWidget>
#include <cstdio>

int main(int argc, char **argv) {
    // Run headless (QT_QPA_PLATFORM=offscreen is set by the test harness).
    QApplication app(argc, argv);
    QTreeWidget tree;
    KTreeWidgetSearchLine searchLine(&tree);
    searchLine.setTreeWidget(&tree);
    if (searchLine.treeWidget() != &tree) {
        std::printf("FAIL: treeWidget mismatch\n");
        return 1;
    }
    std::printf("PASS: KTreeWidgetSearchLine constructed and wired OK\n");
    return 0;
}
