// Consumer-side test for qt5-qtgamepad on OpenHarmony PC.
//
// The OHOS PC host has no physical gamepad (no /dev/input/js* device),
// so runtime gamepad-event behaviour is environment-excluded; this test
// asserts the API logic surface that is reachable without hardware:
//   1. QGamepadManager singleton + empty device list behaviour
//   2. QGamepad default/invalid-device state + property roundtrips
//   3. QGamepadKeyNavigation default keymap + property setters
//   4. QPluginLoader load of the packaged evdev backend plugin
//      (dlopen + Qt plugin metadata contract: IID + Keys=evdev)
#include <QtGamepad/QGamepad>
#include <QtGamepad/QGamepadManager>
#include <QtGamepad/QGamepadKeyNavigation>
#include <QtCore/QPluginLoader>
#include <QtCore/QJsonArray>
#include <QtCore/QJsonObject>
#include <QtCore/QCoreApplication>
#include <QtCore/qglobal.h>
#include <cstdio>

static int g_failed = 0;

#define CHECK(cond) do { \
    if (!(cond)) { \
        std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        ++g_failed; \
    } else { \
        std::printf("PASS %s\n", #cond); \
    } \
} while (false)

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ── 1. QGamepadManager singleton behaviour ──────────────────────
    QGamepadManager *mgr = QGamepadManager::instance();
    CHECK(mgr != nullptr);
    CHECK(QGamepadManager::instance() == mgr);
    CHECK(mgr->connectedGamepads().isEmpty());
    CHECK(!mgr->isGamepadConnected(0));
    CHECK(mgr->gamepadName(0).isEmpty());

    // ── 2. QGamepad default state (no device present) ──────────────
    QGamepad pad(0);
    CHECK(pad.deviceId() == 0);
    CHECK(!pad.isConnected());
    CHECK(pad.name().isEmpty());
    CHECK(pad.axisLeftX() == 0.0);
    CHECK(pad.axisLeftY() == 0.0);
    CHECK(pad.axisRightX() == 0.0);
    CHECK(pad.axisRightY() == 0.0);
    CHECK(!pad.buttonA());
    CHECK(!pad.buttonB());
    CHECK(!pad.buttonX());
    CHECK(!pad.buttonY());
    CHECK(!pad.buttonL1());
    CHECK(!pad.buttonR1());
    CHECK(pad.buttonL2() == 0.0);
    CHECK(pad.buttonR2() == 0.0);
    CHECK(!pad.buttonSelect());
    CHECK(!pad.buttonStart());
    CHECK(!pad.buttonL3());
    CHECK(!pad.buttonR3());
    CHECK(!pad.buttonUp());
    CHECK(!pad.buttonDown());
    CHECK(!pad.buttonLeft());
    CHECK(!pad.buttonRight());
    CHECK(!pad.buttonCenter());
    CHECK(!pad.buttonGuide());
    pad.setDeviceId(42);
    CHECK(pad.deviceId() == 42);

    // ── 3. QGamepadKeyNavigation default keymap + setters ──────────
    QGamepadKeyNavigation kn;
    CHECK(kn.active());
    CHECK(kn.gamepad() == nullptr);
    CHECK(kn.upKey() == Qt::Key_Up);
    CHECK(kn.downKey() == Qt::Key_Down);
    CHECK(kn.leftKey() == Qt::Key_Left);
    CHECK(kn.rightKey() == Qt::Key_Right);
    CHECK(kn.buttonAKey() == Qt::Key_Return);
    CHECK(kn.buttonBKey() == Qt::Key_Back);
    CHECK(kn.buttonXKey() == Qt::Key_Back);
    CHECK(kn.buttonYKey() == Qt::Key_Back);
    CHECK(kn.buttonSelectKey() == Qt::Key_Back);
    CHECK(kn.buttonStartKey() == Qt::Key_Return);
    CHECK(kn.buttonGuideKey() == Qt::Key_Back);
    CHECK(kn.buttonL1Key() == Qt::Key_Back);
    // Upstream copy-paste bug (asserted as-is, real behaviour):
    // buttonR1Key()/buttonR2Key() read the ButtonL2 mapping and
    // buttonR3Key() reads ButtonL3 (qgamepadkeynavigation.cpp getters),
    // so all three return Key_Back, not the Key_Forward the ctor
    // inserts for the R-buttons. Do not "fix" the expectation to match
    // the ctor — the getter source is the shipped API surface.
    CHECK(kn.buttonR1Key() == Qt::Key_Back);
    CHECK(kn.buttonL2Key() == Qt::Key_Back);
    CHECK(kn.buttonR2Key() == Qt::Key_Back);
    CHECK(kn.buttonL3Key() == Qt::Key_Back);
    CHECK(kn.buttonR3Key() == Qt::Key_Back);
    kn.setActive(false);
    CHECK(!kn.active());
    kn.setUpKey(Qt::Key_PageUp);
    CHECK(kn.upKey() == Qt::Key_PageUp);
    kn.setGamepad(&pad);
    CHECK(kn.gamepad() == &pad);

    // ── 4. Packaged evdev backend plugin loads and self-describes ──
    const QString pluginPath =
        QString::fromLocal8Bit(qgetenv("QTGAMEPAD_PLUGIN_PATH"));
    CHECK(!pluginPath.isEmpty());
    QPluginLoader loader(pluginPath);
    CHECK(loader.load());
    if (!loader.isLoaded()) {
        std::printf("loader error: %s\n",
                    loader.errorString().toLocal8Bit().constData());
    }
    const QJsonObject md = loader.metaData();
    CHECK(md.value("IID").toString()
          == QLatin1String(
                 "org.qt-project.Qt.Gamepad.QtGamepadBackendFactoryInterface.5.9"));
    CHECK(md.value("MetaData").toObject().value("Keys").toArray()
          .contains(QLatin1String("evdev")));
    CHECK(loader.unload());

    std::printf("qt5-qtgamepad consumer test: %s (%d assertions failed)\n",
                g_failed == 0 ? "PASS" : "FAIL", g_failed);
    return g_failed == 0 ? 0 : 1;
}
