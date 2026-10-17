// ki18n 6.26.0.1 consumer test.
//
// R34: exercises the real KF6I18n C++ API (link + call + assert), not a
//      version() stub.
// R53: proves the QML module org.kde.ki18n really loads through a fresh
//      offscreen QQmlEngine: `import org.kde.ki18n` resolves the KI18n QML
//      singleton and the KLocalizedContext i18n() context object, and a real
//      KLocalizedContext instance is created. The package-side assertion
//      (qmldir / plugin .so / .qmltypes, plugin DT_NEEDED) is done in
//      test_package/conanfile.py test().
#include <KLocalizedContext>
#include <KLocalizedQmlContext>
#include <KLocalizedString>

#include <QByteArray>
#include <QCoreApplication>
#include <QList>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQmlError>
#include <QString>
#include <QUrl>
#include <QVariant>

#include <cstdio>

static int g_failures = 0;

static void check(bool ok, const char *what)
{
    if (!ok) {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    }
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ---- 1) KLocalizedString C++ API (real linkage) ----
    const QString formatted = ki18nd("ki18n-test", "Number %1 of %2").subs(3).subs(10).toString();
    check(formatted == QStringLiteral("Number 3 of 10"), "KLocalizedString::subs formatting");
    check(ki18nd("ki18n-test", "Hello").toString() == QStringLiteral("Hello"),
          "KLocalizedString passthrough");

    // ---- 2) instantiate the KLocalizedContext context object (R53) ----
    KLocalizedContext context;
    check(context.metaObject() != nullptr, "KLocalizedContext instantiated");
    check(QString::fromLatin1(context.metaObject()->className()).contains(QStringLiteral("KLocalizedContext")),
          "KLocalizedContext class identity");

    // ---- 3) QML module org.kde.ki18n must load from the package ----
    QQmlEngine engine;
    const QByteArray extraImportPath = qgetenv("KI18N_QML_IMPORT_PATH");
    if (!extraImportPath.isEmpty()) {
        const QList<QByteArray> parts = extraImportPath.split(':');
        for (const QByteArray &part : parts) {
            if (!part.isEmpty()) {
                engine.addImportPath(QString::fromLocal8Bit(part));
            }
        }
    }

    KLocalizedQmlContext *qmlContext = KLocalization::setupLocalizedContext(&engine);
    check(qmlContext != nullptr, "KLocalization::setupLocalizedContext returned a context");

    QQmlComponent component(&engine);
    component.setData("import QtQml\n"
                      "import org.kde.ki18n\n"
                      "QtObject {\n"
                      "    property string viaSingleton: KI18n.i18nc(\"Kitten\", \"Meow\")\n"
                      "    property string viaContext: i18n(\"Awesome\")\n"
                      "}\n",
                      QUrl(QStringLiteral("qrc:/ki18n_qml_probe.qml")));

    if (component.isError()) {
        const QList<QQmlError> errors = component.errors();
        for (const QQmlError &error : errors) {
            std::printf("FAIL: QML import/compile error: %s\n", qPrintable(error.toString()));
            ++g_failures;
        }
    } else {
        QObject *object = component.create();
        if (!object) {
            std::printf("FAIL: cannot instantiate a QML object from org.kde.ki18n\n");
            ++g_failures;
        } else {
            check(object->property("viaSingleton").toString() == QStringLiteral("Meow"),
                  "KI18n.i18nc() singleton from org.kde.ki18n");
            check(object->property("viaContext").toString() == QStringLiteral("Awesome"),
                  "KLocalizedContext i18n() context object");
            delete object;
        }
    }

    if (g_failures != 0) {
        std::printf("FAILED: %d check(s)\n", g_failures);
        return 1;
    }
    std::printf("PASS: KF6I18n C++ API + QML module org.kde.ki18n OK\n");
    return 0;
}
