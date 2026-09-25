#include <kdsingleapplication.h>

#include <QtCore/QCoreApplication>
#include <QtCore/QDateTime>
#include <QtCore/QString>

int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    const QString name = QStringLiteral("kdsa-public-api-%1-%2")
                             .arg(QCoreApplication::applicationPid())
                             .arg(QDateTime::currentMSecsSinceEpoch());

    KDSingleApplication instance(name, KDSingleApplication::Option::None);
    if (instance.name() != name)
        return 1;
    if (!instance.isPrimaryInstance())
        return 2;
    return 0;
}
