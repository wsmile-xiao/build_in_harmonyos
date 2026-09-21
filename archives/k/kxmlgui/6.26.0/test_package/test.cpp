// kxmlgui 6.26.0 consumer test (R34: exercises real API).
// Constructs a KXmlGuiWindow and verifies the QMainWindow is usable.
#include <KXmlGuiWindow>
#include <QApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    KXmlGuiWindow win;
    win.setWindowTitle(QStringLiteral("test"));
    if (win.windowTitle() != QStringLiteral("test")) {
        std::printf("FAIL: window title mismatch\n");
        return 1;
    }
    std::printf("PASS: KXmlGuiWindow constructed OK (%s)\n",
                qPrintable(win.windowTitle()));
    return 0;
}
