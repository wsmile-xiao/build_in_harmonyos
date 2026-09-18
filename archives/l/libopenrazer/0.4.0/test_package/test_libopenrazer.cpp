// test_libopenrazer.cpp — libopenrazer 0.4.0 消费者冒烟测试
//
// 在无 OpenRazer D-Bus daemon 的环境下验证：
//   1) 公共头文件可编译、库可链接（Qt6 Core/DBus/Gui/Xml 依赖完整）
//   2) 静态数据 ledFxList 非空（效果枚举表正确导出）
//   3) Manager 可构造（构造仅注册 Qt 元类型，不依赖 daemon 运行）
//   4) isDaemonRunning() 在无 daemon 时安全返回 false（QDBusReply 无效）
//   5) DBusException 可构造并可读 name/message

#include <libopenrazer.h>

#include <QCoreApplication>
#include <QString>

#include <cstdio>

// 注意：openrazer 既存在于全局命名空间（openrazer.h 的元类型工具），
// 又作为 libopenrazer::openrazer（Manager/Device/LED 类）。测试中一律用
// 完整限定名避免歧义。
using namespace libopenrazer;

static int failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("  [PASS] %s\n", msg);                                 \
        } else {                                                               \
            std::printf("  [FAIL] %s\n", msg);                                 \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    std::printf("libopenrazer 0.4.0 consumer smoke test\n");

    // 1) 静态效果枚举表非空（Capability 表由编译期数据构建）
    CHECK(!ledFxList.isEmpty(), "ledFxList is not empty (effect enum table)");

    // 2) 注册元类型（不依赖 D-Bus daemon，纯 Qt 类型系统操作）
    ::openrazer::registerMetaTypes();
    CHECK(QMetaType::type("openrazer::Effect") != QMetaType::UnknownType,
          "openrazer::Effect metatype registered");

    // 3) Manager 构造（构造函数仅注册元类型，不发起 D-Bus 调用）
    libopenrazer::openrazer::Manager manager;
    CHECK(true, "Manager constructed");

    // 4) 无 daemon 时 isDaemonRunning() 返回 false 而不抛异常
    bool running = manager.isDaemonRunning();
    CHECK(!running, "isDaemonRunning() returns false without daemon");

    // 5) DBusException 构造与字段读取
    DBusException ex("org.openrazer.Error", QStringLiteral("test message"));
    CHECK(ex.name() == QLatin1String("org.openrazer.Error"),
          "DBusException name preserved");
    CHECK(ex.message() == QLatin1String("test message"),
          "DBusException message preserved");

    // 6) 元类型可从字符串反查（Q_DECLARE_METATYPE 生效）
    CHECK(QMetaType::type("openrazer::RGB") != QMetaType::UnknownType,
          "openrazer::RGB metatype registered");

    if (failures == 0) {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("%d TEST(S) FAILED\n", failures);
    return 1;
}
