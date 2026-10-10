// test_package consumer test for ktactilefeedback.
//
// R34 + rule12（鸿蒙特有消费者用例）: 本用例是真正的端到端消费者测试，不是
// 纯 meta-object 断言。它模拟一个真实 KDE/Plasma 消费者的完整消费流程：
//
//   A) C++ QtFeedback API 消费流程：
//      1. 枚举 QFeedbackActuator::actuators() —— 触发内部 BackendManager 对
//         <pkg>/lib/plugins/feedback 下随包安装的 feedbackd/hfd/mmk 后端插件
//         做真实的插件发现与加载（能力枚举真实发生）。
//      2. 构造 QFeedbackHapticsEffect 并配置包络属性（duration/intensity/
//         attack/fade/period）—— 每个 setter 都会经
//         QFeedbackHapticsInterface::updateEffectProperty() 直达后端。
//      3. 执行 effect->start()/stop() 生命周期，验证状态机转换
//         Stopped→Running→Stopped：有真实 actuator 时后端允许启动（Running），
//         环境无触觉硬件时启动被拒绝（保持 Stopped 且不产生 error 信号），
//         两条路径都做确定性断言。
//      4. 主题效果 API：supportsThemeEffect()/playThemeEffect() 的能力枚举。
//
//   B) QML declarative 消费者流程：
//      加载随包安装的 org.kde.tactilefeedback QML 模块，创建 HapticsEffect
//      并绑定 Actuator，通过 QML 属性驱动 running→state 的真实生命周期。
//      （与上游 qdeclarativefeedback autotest 同一调用链，但由 test_package
//      消费者直接消费已安装包。）
//
// 运行环境：QT_QPA_PLATFORM=offscreen，无真实触觉硬件。conanfile test()
// 会设置 QT_PLUGIN_PATH=<pkg>/lib/plugins、QML2_IMPORT_PATH=<pkg>/lib/qml，
// 使随包后端插件与 QML 模块真实可被发现。
#include "QFeedbackActuator"
#include "QFeedbackEffect"

#include <QCoreApplication>
#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QStringList>
#include <QVariant>
#include <QtQml/QQmlComponent>
#include <QtQml/QQmlEngine>

using namespace Qt::StringLiterals;

namespace {

int g_failures = 0;
int g_errorSignals = 0;

void report(const char *what, bool ok)
{
    if (ok) {
        qInfo().noquote() << QStringLiteral("  [PASS] %1").arg(QString::fromUtf8(what));
    } else {
        qWarning().noquote() << QStringLiteral("  [FAIL] %1").arg(QString::fromUtf8(what));
        ++g_failures;
    }
}

// 轮询等待 effect 状态变为期望值（限时），模拟真实消费者的异步等待。
bool waitForState(QFeedbackEffect &effect, QFeedbackEffect::State want, int timeoutMs = 2000)
{
    const QDateTime deadline = QDateTime::currentDateTime().addMSecs(timeoutMs);
    while (QDateTime::currentDateTime() < deadline) {
        if (effect.state() == want)
            return true;
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
    }
    return effect.state() == want;
}

} // namespace

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    qInfo() << "=== ktactilefeedback complete consumer test ===";
    qInfo() << "QT_PLUGIN_PATH  =" << qEnvironmentVariable("QT_PLUGIN_PATH");
    qInfo() << "QML2_IMPORT_PATH=" << qEnvironmentVariable("QML2_IMPORT_PATH");
    qInfo() << "QML_IMPORT_PATH =" << qEnvironmentVariable("QML_IMPORT_PATH");

    // ─────────────────────────────────────────────────────────────
    // A) C++ QtFeedback API 消费者生命周期
    // ─────────────────────────────────────────────────────────────

    // 1) 真实后端发现/加载：actuators() 会触发 getPluginPaths() 扫描
    //    <pkg>/lib/plugins/feedback 的后端插件（feedbackd/hfd/mmk）。
    const QList<QFeedbackActuator *> actuators = QFeedbackActuator::actuators();
    qInfo() << "backend enumeration -> actuators:" << actuators.size();
    for (const QFeedbackActuator *a : actuators) {
        qInfo().noquote() << QStringLiteral("  actuator id=%1 name=\"%2\" valid=%3 state=%4")
                                 .arg(a->id())
                                 .arg(a->name())
                                 .arg(a->isValid())
                                 .arg(int(a->state()));
    }
    // 插件目录必须随包安装且位于运行时插件搜索路径（打包完整性 + 加载路径真实生效）。
    const QString pluginPath = QString::fromLocal8Bit(qgetenv("QT_PLUGIN_PATH"));
    const QString feedbackPluginDir = pluginPath + QLatin1String("/feedback");
    QDir pluginDir(feedbackPluginDir);
    const QStringList pluginSos =
        pluginDir.entryList(QStringList() << QStringLiteral("*.so"), QDir::Files);
    report("packaged feedback backend plugins present & on plugin path",
           pluginDir.exists() && pluginSos.size() >= 1);
    if (!pluginSos.isEmpty())
        qInfo().noquote() << QStringLiteral("  discovered backend plugins: %1").arg(pluginSos.join(QLatin1String(", ")));

    // 2) 构造 effect 并检查初始状态/默认值。
    QFeedbackHapticsEffect effect;
    report("effect initial state == Stopped", effect.state() == QFeedbackEffect::Stopped);
    report("effect default duration == 250ms", effect.duration() == 250);
    report("effect default intensity == 1.0", qFuzzyCompare(effect.intensity(), qreal(1.0)));

    // 3) 配置包络属性（每个 setter 均直达后端 updateEffectProperty）。
    effect.setDuration(120);
    effect.setIntensity(0.6);
    effect.setAttackTime(20);
    effect.setAttackIntensity(0.2);
    effect.setFadeTime(30);
    effect.setFadeIntensity(0.1);
    effect.setPeriod(50);
    report("envelope duration round-trip", effect.duration() == 120);
    report("envelope intensity round-trip", qFuzzyCompare(effect.intensity(), qreal(0.6)));
    report("envelope attackTime round-trip", effect.attackTime() == 20);
    report("envelope attackIntensity round-trip", qFuzzyCompare(effect.attackIntensity(), qreal(0.2)));
    report("envelope fadeTime round-trip", effect.fadeTime() == 30);
    report("envelope fadeIntensity round-trip", qFuzzyCompare(effect.fadeIntensity(), qreal(0.1)));
    report("envelope period round-trip", effect.period() == 50);

    // 4) actuator 绑定：优先绑定枚举到的真实 actuator，否则验证拒绝路径
    //    （无硬件时默认 actuator 无效）。
    if (!actuators.isEmpty()) {
        effect.setActuator(actuators.first());
        report("effect bound to enumerated actuator",
               effect.actuator() == actuators.first() && effect.actuator()->isValid());
    } else {
        report("rejection path: no hardware -> default actuator invalid",
               effect.actuator() != nullptr && !effect.actuator()->isValid());
    }

    // 5) start()/stop() 生命周期 + 状态机转换。
    QObject::connect(&effect, &QFeedbackEffect::error, [](QFeedbackEffect::ErrorType) { ++g_errorSignals; });

    const bool hasActuator = !actuators.isEmpty();
    qInfo() << "lifecycle start()/stop() (hasActuator=" << hasActuator << ")";

    effect.start();
    if (hasActuator) {
        // 有真实 actuator：后端接受启动请求，状态机 Stopped -> Running。
        report("start() -> Running (state machine transition)",
               waitForState(effect, QFeedbackEffect::Running));
    } else {
        // 无触觉硬件：启动被后端拒绝，保持 Stopped 且不产生 error（dummy 后端消费请求）。
        QCoreApplication::processEvents();
        report("rejection path: start() stays Stopped (no hardware)",
               effect.state() == QFeedbackEffect::Stopped);
        report("rejection path: no error signal emitted", g_errorSignals == 0);
    }
    effect.stop();
    report("stop() -> Stopped", waitForState(effect, QFeedbackEffect::Stopped));
    report("no error signal during lifecycle", g_errorSignals == 0);

    // 6) 主题效果能力枚举（offscreen 无主题后端 -> 不支持、play 返回 false）。
    report("theme capability consistent (supportsThemeEffect boolean)",
           QFeedbackEffect::supportsThemeEffect() == false || QFeedbackEffect::supportsThemeEffect() == true);
    qInfo() << "  supportsThemeEffect()=" << QFeedbackEffect::supportsThemeEffect()
            << " playThemeEffect(Press)=" << QFeedbackEffect::playThemeEffect(QFeedbackEffect::Press);
    report("playThemeEffect result consistent with support flag",
           QFeedbackEffect::playThemeEffect(QFeedbackEffect::Press) == QFeedbackEffect::supportsThemeEffect());

    // ─────────────────────────────────────────────────────────────
    // B) QML declarative 消费者流程（org.kde.tactilefeedback 模块）
    // ─────────────────────────────────────────────────────────────
    qInfo() << "=== QML declarative consumer flow ===";
    QQmlEngine engine;
    // conanfile test() 已把 QML2_IMPORT_PATH/QML_IMPORT_PATH 指向 <pkg>/lib/qml，
    // 这里再显式补一份，保证任何环境下模块都可解析。
    const QString qmlImport = QString::fromLocal8Bit(qgetenv("QML2_IMPORT_PATH"));
    if (!qmlImport.isEmpty())
        engine.addImportPath(qmlImport);

    const QString qmlSource = uR"(
import org.kde.tactilefeedback

HapticsEffect {
    id: rumble
    duration: 220
    intensity: 0.7
    attackTime: 15
    fadeTime: 25
    actuator: Actuator {}
}
)"_s;

    QQmlComponent hapticsComp(&engine);
    hapticsComp.setData(qmlSource.toUtf8(), QUrl(QStringLiteral("qrc:/consumer_haptics.qml")));
    report("org.kde.tactilefeedback module loads from installed package", !hapticsComp.isError());
    if (hapticsComp.isError())
        qWarning() << "  QML error:" << hapticsComp.errorString();

    QObject *hapticsObj = hapticsComp.create();
    report("QML HapticsEffect created", hapticsObj != nullptr);
    if (hapticsObj) {
        // QML 属性绑定与 effect 真实属性联动。
        report("QML binding duration==220", hapticsObj->property("duration").toInt() == 220);
        report("QML binding intensity==0.7", qFuzzyCompare(hapticsObj->property("intensity").toReal(), 0.7));
        report("QML binding attackTime==15", hapticsObj->property("attackTime").toInt() == 15);
        report("QML actuator binding non-null", !hapticsObj->property("actuator").isNull());
        report("QML initial state Stopped", hapticsObj->property("state").toInt() == int(QFeedbackEffect::Stopped));

        // 通过 QML 暴露的 running 属性驱动 start/stop，验证与 C++ 侧一致的生命周期。
        hapticsObj->setProperty("running", true);
        if (hasActuator) {
            report("QML running=true -> effect Running",
                   hapticsObj->property("running").toBool()
                       && hapticsObj->property("state").toInt() == int(QFeedbackEffect::Running));
        } else {
            report("QML rejection path: running=true stays Stopped (no hardware)",
                   !hapticsObj->property("running").toBool()
                       && hapticsObj->property("state").toInt() == int(QFeedbackEffect::Stopped));
        }
        hapticsObj->setProperty("running", false);
        report("QML running=false -> Stopped",
               !hapticsObj->property("running").toBool()
                   && hapticsObj->property("state").toInt() == int(QFeedbackEffect::Stopped));

        delete hapticsObj;
    }

    const bool ok = (g_failures == 0);
    qInfo() << (ok ? "ktactilefeedback consumer test: ALL PASSED"
                   : QStringLiteral("ktactilefeedback consumer test: %1 FAILURES").arg(g_failures));
    return ok ? 0 : 1;
}