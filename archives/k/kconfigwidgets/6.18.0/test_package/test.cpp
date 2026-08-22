// kconfigwidgets 6.18.0 consumer test (R34: exercises real API).
// Constructs a KConfigDialog and verifies dialog registration/page handling.
#include <KConfigDialog>
#include <KCoreConfigSkeleton>
#include <QApplication>
#include <QString>
#include <QWidget>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);

    const QString dialogName = QStringLiteral("test-dialog");
    if (KConfigDialog::exists(dialogName) != nullptr) {
        std::fprintf(stderr, "FAIL: dialog unexpectedly exists before construction\n");
        return 1;
    }

    KCoreConfigSkeleton config(QStringLiteral("test-kconfigwidgetsrc"));
    {
        KConfigDialog dialog(nullptr, dialogName, &config);
        if (KConfigDialog::exists(dialogName) != &dialog) {
            std::fprintf(stderr, "FAIL: constructed dialog was not registered\n");
            return 1;
        }

        auto *item = dialog.addPage(new QWidget(), QStringLiteral("General"));
        if (item == nullptr) {
            std::fprintf(stderr, "FAIL: addPage returned nullptr\n");
            return 1;
        }
        if (dialog.currentPage() != item) {
            std::fprintf(stderr, "FAIL: currentPage does not match added page\n");
            return 1;
        }
    }

    if (KConfigDialog::exists(dialogName) != nullptr) {
        std::fprintf(stderr, "FAIL: dialog remained registered after destruction\n");
        return 1;
    }

    std::printf("PASS: KConfigDialog construction, exists(), addPage(), and teardown OK\n");
    return 0;
}
