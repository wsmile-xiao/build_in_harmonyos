#include <QCoreApplication>
#include <QSqlDatabase>
#include <QDBusConnection>
#include <QDebug>

// 变体核心卖点真实功能验证（非空转）：
// 1) Sql  —— QSQLITE 驱动必须可用（qtbase-sql-dbus 变体的 Sql 组件）
// 2) DBus —— QtDBus 类型/链接可用（QT_NO_DBUS 宏污染修复后）
int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // Sql 核心卖点：QSQLITE 驱动可用性（坏掉则测试失败）
    if (!QSqlDatabase::isDriverAvailable("QSQLITE")) {
        qCritical() << "FAIL: QSQLITE driver not available (Sql component broken)";
        return 1;
    }

    // DBus 核心卖点：QtDBus 编译链接可用（QT_NO_DBUS 修复验证）。
    // 无总线环境（headless）不视为失败——isConnected() 为 false 仅表示无 session bus。
    QDBusConnection conn = QDBusConnection::sessionBus();
    if (!conn.isConnected()) {
        qWarning() << "session bus not connected (headless env, non-fatal)";
    }

    qInfo() << "PASS: QSQLITE driver OK + QtDBus available";
    return 0;
}
