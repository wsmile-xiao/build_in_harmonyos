// test_qt6linguist.cpp — Qt6LinguistTools 6.11.1 测试源
// 真实消费 Qt6::Core（Qt6LinguistTools 依赖的基座），并在 main 中链接
// Qt6::Core 以验证 find_package(Qt6 COMPONENTS Core LinguistTools) 目标可解析。
#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    const QString msg = QStringLiteral("Hello");
    if (msg != QStringLiteral("Hello")) {
        std::fprintf(stderr, "FAIL: QString roundtrip mismatch\n");
        return 1;
    }
    std::printf("OK: Qt6LinguistTools consumer links Qt6::Core, q=%d\n",
                static_cast<int>(msg.size()));
    return 0;
}
