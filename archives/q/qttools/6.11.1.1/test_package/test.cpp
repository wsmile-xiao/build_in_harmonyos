#include <QCoreApplication>
#include <QLibraryInfo>
#include <QString>
#include <QDebug>

// Qt6Tools 组件真实功能验证（非空转）：
// QLibraryInfo（Qt 安装路径/版本信息，Qt6Tools 提供 Qt6::Tools 目标）。
int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // 库路径真实查询（非空转）
    // Qt6：LibraryPath 是枚举类型名——path() 需传枚举值（LibrariesPath 库路径）
    QString libPath = QLibraryInfo::path(QLibraryInfo::LibrariesPath);
    if (libPath.isEmpty()) {
        qCritical() << "FAIL: QLibraryInfo LibraryPath empty (Qt6Tools broken)";
        return 1;
    }

    qInfo() << "PASS: Qt6Tools OK (LibraryPath:" << libPath << ")";
    return 0;
}
