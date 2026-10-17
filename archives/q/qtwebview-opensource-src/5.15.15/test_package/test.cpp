#include <QCoreApplication>
#include <QtWebView>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // Call QtWebView::initialize() to verify the library loads and
    // its API is callable. This registers QML types for the WebView
    // module — with the null backend it succeeds without web rendering.
    QtWebView::initialize();

    std::printf("QtWebView test PASSED\n");
    return 0;
}
