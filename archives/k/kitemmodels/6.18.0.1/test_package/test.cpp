// kitemmodels 6.18.0.1 consumer test.
//
// R34: exercises the real KF6ItemModels C++ API (link + call + assert).
// R53: proves the QML module org.kde.kitemmodels is present in the package,
//      importable through a fresh QQmlEngine pointed at the package import
//      path, and that its QML types instantiate and behave correctly.
#include <KModelIndexProxyMapper>
#include <KNumberModel>

#include <QAbstractItemModel>
#include <QCoreApplication>
#include <QModelIndex>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QString>
#include <QStringList>
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

    // ---- 1) KItemModels C++ API (real linkage, not a version() stub) ----
    KNumberModel model;
    model.setMinimumValue(1.0);
    model.setMaximumValue(3.0);
    model.setStepSize(1.0);
    check(model.rowCount() == 3, "KNumberModel::rowCount() != 3");
    check(model.data(model.index(1, 0), KNumberModel::ValueRole).toDouble() == 2.0,
          "KNumberModel ValueRole != 2.0");

    KModelIndexProxyMapper mapper(&model, &model);
    const QModelIndex source = model.index(1, 0);
    const QModelIndex mapped = mapper.mapLeftToRight(source);
    check(mapped.isValid(), "KModelIndexProxyMapper::mapLeftToRight returned invalid");
    check(mapper.mapRightToLeft(mapped) == source, "KModelIndexProxyMapper round-trip mismatch");

    // ---- 2) QML module org.kde.kitemmodels must load from the package ----
    QQmlEngine engine;
    const QByteArray extraImportPath = qgetenv("KITEMMODELS_QML_IMPORT_PATH");
    if (!extraImportPath.isEmpty()) {
        const QStringList parts =
            QString::fromLocal8Bit(extraImportPath).split(QLatin1Char(':'), Qt::SkipEmptyParts);
        for (const QString &part : parts) {
            engine.addImportPath(part);
        }
    }

    QQmlComponent component(&engine);
    component.setData(
        "import QtQml\n"
        "import org.kde.kitemmodels\n"
        "KSortFilterProxyModel {\n"
        "    sourceModel: KNumberModel { minimumValue: 1; maximumValue: 10; stepSize: 1 }\n"
        "    filterRowCallback: function(source_row, source_parent) {\n"
        "        return sourceModel.data(sourceModel.index(source_row, 0, source_parent), Qt.DisplayRole) % 2 === 1;\n"
        "    }\n"
        "}\n",
        QUrl(QStringLiteral("qrc:/kitemmodels_qml_probe.qml")));

    if (component.isError()) {
        const auto errors = component.errors();
        for (const QQmlError &error : errors) {
            std::printf("FAIL: QML import/compile error: %s\n", qPrintable(error.toString()));
            ++g_failures;
        }
    } else {
        QObject *object = component.create();
        if (!object) {
            std::printf("FAIL: cannot instantiate a QML type from org.kde.kitemmodels\n");
            ++g_failures;
        } else {
            auto *proxy = qobject_cast<QAbstractItemModel *>(object);
            check(proxy != nullptr, "QML KSortFilterProxyModel is not a QAbstractItemModel");
            if (proxy) {
                check(proxy->rowCount() == 5,
                      "QML KSortFilterProxyModel rowCount != 5 (odd numbers in 1..10)");
            }
            delete object;
        }
    }

    if (g_failures != 0) {
        std::printf("FAILED: %d check(s)\n", g_failures);
        return 1;
    }
    std::printf("PASS: KItemModels C++ API + QML module org.kde.kitemmodels OK\n");
    return 0;
}
