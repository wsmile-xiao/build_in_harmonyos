#include <QCoreApplication>
#include <QDebug>
#include <QSqlDatabase>
#include <QSqlError>
#include <QSqlQuery>
#include <QSqlRecord>
#include <QSqlTableModel>
#include <QTemporaryDir>
#include <QVariant>
#include <cstdlib>

// 检查数据库行为，失败时返回非零退出码并输出具体原因。
static void require(bool condition, const char *message)
{
    if (!condition) {
        qCritical().noquote() << QString::fromUtf8(message);
        std::exit(1);
    }
}

// 使用安装后的 SQL 库和插件验证持久化、参数绑定、事务及数据模型。
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QTemporaryDir directory;
    require(directory.isValid(), "无法创建测试目录");
    require(QSqlDatabase::isDriverAvailable("QSQLITE"), "未找到 SQLite 驱动");
    QSqlDatabase db = QSqlDatabase::addDatabase("QSQLITE");
    db.setDatabaseName(directory.filePath("contacts.db"));
    require(db.open(), "无法打开 SQLite 数据库");
    {
        QSqlQuery query(db);
        require(query.exec("CREATE TABLE contacts(id INTEGER PRIMARY KEY, name TEXT, payload BLOB)"), "建表失败");
        require(db.transaction(), "开启事务失败");
        require(query.prepare("INSERT INTO contacts VALUES(:id, :name, :payload)"), "预处理失败");
        query.bindValue(":id", 7);
        query.bindValue(":name", QString::fromUtf8("鸿蒙联系人"));
        query.bindValue(":payload", QByteArray::fromHex("00017fff"));
        require(query.exec(), "参数绑定插入失败");
        require(db.commit(), "提交事务失败");
        require(query.exec("SELECT name, payload FROM contacts WHERE id=7") && query.next(), "查询失败");
        require(query.value(0).toString() == QString::fromUtf8("鸿蒙联系人"), "中文数据不一致");
        require(query.value(1).toByteArray() == QByteArray::fromHex("00017fff"), "二进制数据不一致");
        query.finish();
        require(db.transaction(), "第二次开启事务失败");
        require(query.exec("DELETE FROM contacts"), "事务内删除失败");
        require(db.rollback(), "回滚失败");
        require(query.exec("SELECT COUNT(*) FROM contacts") && query.next() && query.value(0).toInt() == 1,
                "回滚未恢复数据");
        query.finish();
        QSqlTableModel model(nullptr, db);
        model.setTable("contacts");
        require(model.select() && model.rowCount() == 1, "SQL 模型加载失败");
        require(model.record(0).value("name").toString() == QString::fromUtf8("鸿蒙联系人"), "模型数据不一致");
    }
    db.close();
    require(db.open(), "重新打开数据库失败");
    {
        QSqlQuery query(db);
        require(query.exec("SELECT id FROM contacts") && query.next() && query.value(0).toInt() == 7,
                "数据库持久化失败");
    }
    db.close();
    db = QSqlDatabase();
    QSqlDatabase::removeDatabase(QSqlDatabase::defaultConnection);
    qInfo() << "QtSql 消费者验证通过";
    return 0;
}
