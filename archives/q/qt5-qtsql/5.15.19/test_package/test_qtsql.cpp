#include <QSqlDatabase>
#include <QSqlQuery>
#include <QSqlError>
#include <QVariant>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    QSqlDatabase db = QSqlDatabase::addDatabase("QSQLITE");
    db.setDatabaseName(":memory:");
    if (!db.open()) {
        printf("FAIL: cannot open :memory: db: %s\n", db.lastError().text().toUtf8().constData());
        return 1;
    }
    QSqlQuery q;
    if (!q.exec("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")) {
        printf("FAIL: create: %s\n", q.lastError().text().toUtf8().constData());
        return 1;
    }
    if (!q.exec("INSERT INTO t (name) VALUES ('hello-ohos')")) {
        printf("FAIL: insert: %s\n", q.lastError().text().toUtf8().constData());
        return 1;
    }
    if (!q.exec("SELECT id, name FROM t")) {
        printf("FAIL: select: %s\n", q.lastError().text().toUtf8().constData());
        return 1;
    }
    if (!q.next()) {
        printf("FAIL: no row\n");
        return 1;
    }
    const int id = q.value(0).toInt();
    const QString name = q.value(1).toString();
    if (id != 1 || name != QString("hello-ohos")) {
        printf("FAIL: roundtrip mismatch id=%d name=%s\n", id, name.toUtf8().constData());
        return 1;
    }
    printf("PASS: QSQLITE :memory: create/insert/select roundtrip OK (id=%d name=%s)\n",
           id, name.toUtf8().constData());
    return 0;
}
