#include <QApplication>
#include <QBuffer>
#include <QObject>
#include <QUiLoader>
#include <QWidget>
#include <QtCore/QString>
#include <cstdio>

// Consumer test for the Qt Tools package on HarmonyOS PC.
// Exercises the installed Qt6::UiTools API (QUiLoader), the runtime
// library shipped by qttools (libQt6UiTools). Requires QApplication
// (QWidget) and QT_QPA_PLATFORM=offscreen on headless OHOS.

static int failures = 0;

#define CHECK(cond, name)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("[PASS] %s\n", name);                                  \
        } else {                                                               \
            std::printf("[FAIL] %s\n", name);                                  \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    // 1. QUiLoader construction (Qt6 API).
    QUiLoader loader;
    CHECK(loader.isLanguageChangeEnabled() == false,
          "QUiLoader isLanguageChangeEnabled defaults to false");

    // 2. Load a minimal <widget> UI from a QBuffer.
    QBuffer buffer;
    buffer.setData("<ui version=\"4.0\">"
                   "<class>Form</class>"
                   "<widget class=\"QWidget\" name=\"Form\">"
                   "<property name=\"geometry\"><rect><x>0</x><y>0</y>"
                   "<width>100</width><height>50</height></rect></property>"
                   "</widget>"
                   "</ui>");
    buffer.open(QIODevice::ReadOnly);
    QWidget *widget = loader.load(&buffer, nullptr);
    CHECK(widget != nullptr, "QUiLoader::load minimal widget");
    if (widget) {
        CHECK(widget->objectName() == QStringLiteral("Form"),
              "loaded widget objectName == Form");
        delete widget;
    }

    std::printf("qttools consumer test: %s\n",
                failures == 0 ? "ALL PASSED" : "FAILED");
    return failures == 0 ? 0 : 1;
}
