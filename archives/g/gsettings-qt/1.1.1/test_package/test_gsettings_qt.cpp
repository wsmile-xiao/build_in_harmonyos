/* test_gsettings_qt.cpp — gsettings-qt 1.1.1 (HarmonyOS PC) 消费方验证
 *
 * 实质性调用被测包的公开 API（QGSettings），在 GSETTINGS_BACKEND=memory 与
 * 测试 schema 下完成读写/重置/键枚举/默认值/枚举值/变更信号验证。
 */

#include <QCoreApplication>
#include <QGSettings>
#include <QStringList>
#include <QVariant>

#include <cstdio>

static int g_failures = 0;

static void check(bool condition, const char *what)
{
    if (condition) {
        std::printf("PASS: %s\n", what);
    } else {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    }
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    check(QGSettings::isSchemaInstalled("com.ubports.gsettings.adt"),
          "isSchemaInstalled(com.ubports.gsettings.adt) == true");
    check(!QGSettings::isSchemaInstalled("com.ubports.gsettings.absent"),
          "isSchemaInstalled(com.ubports.gsettings.absent) == false");

    QGSettings settings("com.ubports.gsettings.adt");

    check(settings.get("testInteger").toInt() == 42, "default testInteger == 42");
    check(settings.defaultValue("testInteger").toInt() == 42,
          "defaultValue(testInteger) == 42");
    check(settings.defaultValue("testDouble").toDouble() == 1.5,
          "defaultValue(testDouble) == 1.5");
    check(settings.choices("testChoice").size() == 3,
          "choices(testChoice).size() == 3");

    settings.set(QStringLiteral("testInteger"), 7);
    check(settings.get("testInteger").toInt() == 7, "after set testInteger == 7");

    bool changed = false;
    QObject::connect(&settings, &QGSettings::changed,
                     [&changed](const QString &) { changed = true; });
    settings.set(QStringLiteral("testString"), QStringLiteral("harmonyos"));
    app.processEvents();
    check(changed, "changed() signal emitted after set");
    check(settings.get("testString").toString() == QStringLiteral("harmonyos"),
          "after set testString == harmonyos");
    check(settings.trySet(QStringLiteral("testString"), QStringLiteral("ohos")),
          "trySet(testString, ohos) == true");

    settings.reset(QStringLiteral("testInteger"));
    check(settings.get("testInteger").toInt() == 42, "after reset testInteger == 42");

    const QStringList keys = settings.keys();
    check(keys.contains(QStringLiteral("testInteger")), "keys() contains testInteger");
    check(keys.contains(QStringLiteral("testString")), "keys() contains testString");

    std::printf("%s: %d failure(s)\n", g_failures == 0 ? "OK" : "FAILED", g_failures);
    return g_failures == 0 ? 0 : 1;
}
