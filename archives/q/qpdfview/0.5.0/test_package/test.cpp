// qpdfview 插件端到端测试：dlopen bin/libqpdfview_pdf.so，通过 qpdfview::Plugin
// 接口真实加载 PDF、渲染页面、抽取文本。无 GUI 交互（offscreen QPA）。
#include <QGuiApplication>
#include <QPluginLoader>
#include <QImage>
#include <QFileInfo>
#include <QDir>
#include <QDebug>
#include <cstdio>

#include "model.h"

static int failures = 0;

static void check(bool ok, const char* what)
{
    std::printf("%s %s\n", ok ? "[pass]" : "[fail]", what);
    if(!ok) ++failures;
}

int main(int argc, char** argv)
{
    if(argc < 4)
    {
        std::printf("usage: %s <plugin-dir> <plugin-name> <pdf-file>\n", argv[0]);
        return 2;
    }

    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);

    const QString pluginDir = QString::fromLocal8Bit(argv[1]);
    const QString pluginName = QString::fromLocal8Bit(argv[2]);
    const QString pdfPath = QString::fromLocal8Bit(argv[3]);

    const QString pluginPath = QDir(pluginDir).absoluteFilePath(pluginName);
    check(QFileInfo::exists(pluginPath), "pdf plugin file exists");

    QPluginLoader loader(pluginPath);
    QObject* object = loader.instance();
    if(!object)
    {
        std::printf("[fail] plugin load: %s\n", qPrintable(loader.errorString()));
        return 1;
    }
    check(true, "pdf plugin dlopen + instance");
    check(loader.metaData().value("IID").toString() == QStringLiteral("local.qpdfview.Plugin"),
          "plugin IID == local.qpdfview.Plugin");

    qpdfview::Plugin* plugin = qobject_cast< qpdfview::Plugin* >(object);
    if(!plugin)
    {
        std::printf("[fail] qobject_cast<qpdfview::Plugin*> failed\n");
        return 1;
    }
    check(true, "qobject_cast to qpdfview::Plugin");

    qpdfview::Model::Document* document = plugin->loadDocument(pdfPath);
    check(document != 0, "loadDocument() returns a document");
    if(!document) return 1;

    check(document->numberOfPages() == 1, "numberOfPages() == 1");

    qpdfview::Model::Page* page = document->page(0);
    check(page != 0, "page(0)");
    if(!page) return 1;

    const QSizeF size = page->size();
    check(qAbs(size.width() - 300.0) < 1.0 && qAbs(size.height() - 120.0) < 1.0,
          "page size == 300x120 pt (from MediaBox)");

    // 文本抽取走 poppler 的 TextOutputDev：证明 poppler 真正解析了内容流。
    const QString text = page->text(QRectF(0, 0, 300, 120));
    std::printf("       extracted text: %s\n", qPrintable(text.trimmed()));
    check(text.contains(QStringLiteral("Hello HarmonyOS")), "text() extracts 'Hello HarmonyOS'");

    const QList< QRectF > hits = page->search(QStringLiteral("HarmonyOS"), false, false);
    check(!hits.isEmpty(), "search('HarmonyOS') finds the string");

    // 真实渲染：splash/QPainter 后端输出 QImage。
    const QImage image = page->render(144.0, 144.0, qpdfview::RotateBy0);
    check(!image.isNull(), "render() returns a valid QImage");
    check(image.width() == 600 && image.height() == 240,
          "render(144dpi) == 600x240 px");
    if(!image.isNull())
    {
        bool ink = false;
        for(int y = 0; y < image.height() && !ink; ++y)
            for(int x = 0; x < image.width(); ++x)
                if(qGray(image.pixel(x, y)) < 128) { ink = true; break; }
        check(ink, "rendered page contains non-white pixels (text actually drawn)");
        image.save(QDir::current().absoluteFilePath("qpdfview-render.png"));
    }

    delete document;

    std::printf("%s: %d failure(s)\n", failures ? "FAILED" : "PASSED", failures);
    return failures ? 1 : 0;
}
