#include <ElaWidget.h>
#include <QApplication>
int main(int argc, char *argv[]) {
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication app(argc, argv);
    ElaWidget widget;
    widget.setWindowTitle("ElaWidgetTools Test");
    if (widget.windowTitle() != "ElaWidgetTools Test") return 1;
    return 0;
}
