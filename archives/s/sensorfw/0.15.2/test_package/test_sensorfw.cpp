/**
 * test_package/test_sensorfw.cpp — sensorfw/0.15.2 消费者功能测试（OHOS PC / aarch64）
 *
 * 由 conan create 编译并真实执行：它链接**被测包**的 libsensorclient-qt5 /
 * libsensordatatypes-qt5 与随包发布的头文件，因此一个缺符号、缺头文件、
 * 装错版本或装错路径的包会直接让构建失败，而不是静默通过。
 *
 * 三个消费者用例（与 test.sh 的 shell 用例统一编号，共 6 个）：
 *   consumer.api.types   数据类型 API 真实往返（TimedXyzData / TimedUnsigned /
 *                        CompassData 字段与时间戳）
 *   consumer.api.qtmeta  XYZ QObject 门面：直接取值 + 经 QObject::property()
 *                        走 Qt 元对象系统取值 + 元对象类名（真实运行期行为）。
 *                        XYZ 的 TimedXyzData 构造函数在 datatypes/xyz.cpp（非
 *                        inline），故本用例对 libsensordatatypes-qt5 构成真实的
 *                        链接依赖。
 *   consumer.ohos.dlopen **鸿蒙特有**：把包内 lib/sensord-qt5/ 下每个插件用
 *                        RTLD_NOW 打开并解析入口点，全部必须成功 —— 直接验证
 *                        0004 补丁（插件自带 DT_NEEDED libsensorfw-qt5）。在
 *                        适配前的原始上游代码上，本用例必然失败：
 *                        Error relocating libXxx-qt5.so:
 *                        _ZN15InputDevAdaptorC2ERK7QStringi: symbol not found
 *                        因为 HarmonyOS/musl 的 dlopen 只在对象自身 DT_NEEDED
 *                        闭包内解析未定义符号。
 *
 * 输出协议（test.sh 解析）：
 *   "  [case] <name>"                      用例开始
 *   "     ok   <what>" / "     FAIL <what>" 单条断言
 *   "  [result] <name> PASS|FAIL checks=N failed=M"  用例结束
 *   "== checks: N passed: M failed: K"     全程序汇总（最后一行）
 */
#include <dirent.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include <algorithm>
#include <string>
#include <vector>

#include <QCoreApplication>
#include <QMetaObject>
#include <QObject>
#include <QVariant>

#include <datatypes/genericdata.h>
#include <datatypes/orientationdata.h>
#include <datatypes/timedunsigned.h>
#include <datatypes/xyz.h>

static int g_checks = 0;
static int g_failed = 0;

static const char *g_case = "";
static int g_case_checks = 0;
static int g_case_failed = 0;

static void case_begin(const char *name)
{
    g_case = name;
    g_case_checks = 0;
    g_case_failed = 0;
    printf("  [case] %s\n", name);
}

static void case_end()
{
    printf("  [result] %s %s checks=%d failed=%d\n", g_case,
           g_case_failed == 0 ? "PASS" : "FAIL", g_case_checks, g_case_failed);
}

static void check(bool ok, const std::string &what)
{
    ++g_checks;
    ++g_case_checks;
    if (ok) {
        printf("     ok   %s\n", what.c_str());
    } else {
        ++g_failed;
        ++g_case_failed;
        printf("     FAIL %s\n", what.c_str());
    }
}

// ── consumer.api.types ──────────────────────────────────────────────────────
static void case_types()
{
    case_begin("consumer.api.types");

    TimedXyzData xyz(0x1122334455667788ULL, 1.5f, -2.5f, 3.25f);
    check(xyz.timestamp_ == 0x1122334455667788ULL, "TimedXyzData timestamp round-trip");
    check(xyz.x_ == 1.5f && xyz.y_ == -2.5f && xyz.z_ == 3.25f,
          "TimedXyzData x/y/z round-trip");

    TimedXyzData copy(xyz);
    check(copy.timestamp_ == xyz.timestamp_ && copy.x_ == xyz.x_ &&
              copy.y_ == xyz.y_ && copy.z_ == xyz.z_,
          "TimedXyzData copy construction is value-equal");

    TimedUnsigned counter(42ULL, 7u);
    check(counter.timestamp_ == 42ULL && counter.value_ == 7u,
          "TimedUnsigned timestamp/value round-trip");

    // 5 参构造： (timestamp, degrees, level, correctedDegrees, rawDegrees)
    CompassData compass(99ULL, 12, 3, 350, 12);
    check(compass.timestamp_ == 99ULL, "CompassData timestamp round-trip");
    check(compass.degrees_ == 12, "CompassData degrees round-trip");
    check(compass.level_ == 3, "CompassData level round-trip");
    check(compass.correctedDegrees_ == 350, "CompassData correctedDegrees round-trip");
    check(compass.rawDegrees_ == 12, "CompassData rawDegrees round-trip");

    case_end();
}

// ── consumer.api.qtmeta ─────────────────────────────────────────────────────
// XYZ 的构造函数定义在 datatypes/xyz.cpp（非 inline），因此本用例对
// libsensordatatypes-qt5 构成真实的链接依赖；property() 取值走 Qt 元对象系统。
static void case_qtmeta()
{
    case_begin("consumer.api.qtmeta");

    TimedXyzData src(7ULL, 4.0f, 5.0f, 6.0f);
    XYZ facade(src);

    check(facade.x() == 4.0f && facade.y() == 5.0f && facade.z() == 6.0f,
          "XYZ facade getters return the wrapped values");

    check(facade.XYZData().timestamp_ == 7ULL && facade.XYZData().x_ == 4.0f,
          "XYZData() returns the wrapped TimedXyzData");

    // Q_PROPERTY(int x READ x) 声明为 int（getter 返回 float），故经元对象
    // 系统读回时按声明类型取整；用整数值的输入保证结果确定。
    const QVariant vx = facade.property("x");
    const QVariant vy = facade.property("y");
    const QVariant vz = facade.property("z");
    check(vx.isValid() && vy.isValid() && vz.isValid(),
          "Q_PROPERTY x/y/z are exposed through the meta-object system");
    check(vx.toInt() == 4 && vy.toInt() == 5 && vz.toInt() == 6,
          "Q_PROPERTY values read back through QObject::property()");

    const QMetaObject *mo = facade.metaObject();
    check(mo != NULL && strcmp(mo->className(), "XYZ") == 0,
          "metaObject()->className() == \"XYZ\"");

    case_end();
}

// ── consumer.ohos.dlopen ────────────────────────────────────────────────────
//
// One of the 47 packaged modules is not a Qt plugin: the upstream
// adaptors/magnetometeradaptor-ascii/magnetometeradaptor-asciiplugin.h declares
//
//     class MagnetometerAdaptorAsciiPlugin : public Plugin
//
// i.e. it derives from sensorfw's own Plugin base and carries no
// Q_PLUGIN_METADATA(...), so moc emits no qt_plugin_query_metadata entry point
// for it.  Verified with readelf --dyn-syms over all 47 packaged plugins:
// 46 expose qt_plugin_query_metadata, this one does not.  It is still a real
// shared object that must satisfy the DT_NEEDED requirement, so only the
// metadata assertion is waived - and only for this explicitly named module, so
// a regression that strips metadata from a genuine Qt plugin still fails.
static const char *g_non_qt_plugins[] = {
    "libmagnetometeradaptor-ascii-qt5.so",
};
static const int g_non_qt_plugin_count =
    static_cast<int>(sizeof(g_non_qt_plugins) / sizeof(g_non_qt_plugins[0]));

static bool is_known_non_qt_plugin(const std::string &name)
{
    for (int i = 0; i < g_non_qt_plugin_count; ++i) {
        if (name == g_non_qt_plugins[i]) {
            return true;
        }
    }
    return false;
}

static void case_dlopen(const std::string &pluginDir)
{
    case_begin("consumer.ohos.dlopen");

    DIR *dir = opendir(pluginDir.c_str());
    if (!dir) {
        check(false, "cannot open plugin directory " + pluginDir);
        case_end();
        return;
    }

    std::vector<std::string> plugins;
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        const std::string name(entry->d_name);
        if (name.size() > 3 && name.compare(name.size() - 3, 3, ".so") == 0) {
            plugins.push_back(name);
        }
    }
    closedir(dir);

    std::sort(plugins.begin(), plugins.end());  // 稳定顺序，便于日志比对

    check(plugins.size() >= 40,
          "package ships the plugin set (" + std::to_string(plugins.size()) +
              " plugins in lib/sensord-qt5/)");

    const int total = static_cast<int>(plugins.size());
    int loaded = 0;         // dlopen(RTLD_NOW) 成功
    int with_metadata = 0;  // 且解析出 Qt 插件入口点
    int exempt = 0;         // 已记录的「非 Qt 插件」模块
    int dlopen_failed = 0;

    for (int i = 0; i < total; ++i) {
        const std::string path = pluginDir + "/" + plugins[i];
        void *handle = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!handle) {
            const char *err = dlerror();
            ++dlopen_failed;
            check(false, plugins[i] + " dlopen(RTLD_NOW) failed: " +
                             (err ? err : "(no error string)"));
            continue;
        }
        ++loaded;
        if (is_known_non_qt_plugin(plugins[i])) {
            ++exempt;
        } else if (dlsym(handle, "qt_plugin_query_metadata") != NULL) {
            ++with_metadata;
        } else {
            check(false, plugins[i] +
                             " loads but exposes no qt_plugin_query_metadata");
        }
        dlclose(handle);
    }

    check(dlopen_failed == 0,
          "every packaged plugin loads with RTLD_NOW (" + std::to_string(loaded) +
              "/" + std::to_string(total) + ")");

    // 真正的 Qt 插件都必须能被 Qt 识别为插件
    check(with_metadata == total - exempt,
          "every Qt plugin exposes qt_plugin_query_metadata (" +
              std::to_string(with_metadata) + "/" +
              std::to_string(total - exempt) + ")");

    // 例外清单本身也要被守住：模块被删掉或被改名都应当失败
    check(exempt == g_non_qt_plugin_count,
          "documented non-Qt-plugin module present (" + std::to_string(exempt) +
              "/" + std::to_string(g_non_qt_plugin_count) + ")");

    case_end();
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <package plugin dir>\n", argv[0]);
        return 2;
    }
    QCoreApplication app(argc, argv);

    printf("== sensorfw consumer test (OHOS aarch64)\n");
    printf("   Qt %s / plugin dir %s\n", qVersion(), argv[1]);

    case_types();
    case_qtmeta();
    case_dlopen(argv[1]);

    printf("== checks: %d passed: %d failed: %d\n", g_checks, g_checks - g_failed,
           g_failed);
    return g_failed == 0 ? 0 : 1;
}
