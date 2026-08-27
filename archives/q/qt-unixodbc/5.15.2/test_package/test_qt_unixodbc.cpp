#include <QtCore/qcoreapplication.h>
#include <QtCore/qdebug.h>
#include <QtCore/qstringlist.h>
#include <QtSql/qsqldatabase.h>
#include <QtSql/qsqldriver.h>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    QStringList drivers = QSqlDatabase::drivers();
    QSqlDatabase db = QSqlDatabase::addDatabase("QODBC3");
    QString connName = db.connectionName();
    QString drvName = db.driverName();
    if (connName.isEmpty()) return 1;
    if (drvName != "QODBC3") return 2;
    qDebug() << "SQL drivers:" << drivers << "conn:" << connName << "drv:" << drvName;
    return 0;
}
