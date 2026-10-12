// test_package for qt5-qtsensors 5.15.2 (consumer-side smoke test)
//
// QtSensors 的硬件后端依赖真机传感器设备（/dev/input、系统 D-Bus 等），
// OHOS PC 无传感器硬件节点，本消费者侧测试按 TEST_QUALITY_SPEC：
//   * 类型常量/传感器对象状态机（未激活/无读数/属性 roundtrip）等
//     纯逻辑路径全部断言；
//   * 软件手势识别插件（QSensorGestureManager，纯软件实现、无需硬件）
//     验证插件加载与注册（QtSensors.shake 等识别器在包内注册）；
//   * QML 模块（QtSensors import）创建 QmlAccelerometer 对象验证
//     QML 插件与 C++ 库的链接完整性。
#include <QCoreApplication>
#include <QSensor>
#include <QAccelerometer>
#include <QCompass>
#include <QSensorGestureManager>
#include <QQmlEngine>
#include <QQmlComponent>
#include <QUrl>
#include <QStringList>
#include <QVariant>
#include <cstdio>

static int g_failures = 0;

#define CHECK(cond, name)                                      \
    do {                                                       \
        bool ok_ = (cond);                                     \
        std::printf("%s : %s\n", ok_ ? "PASS" : "FAIL", name); \
        if (!ok_) { g_failures++; }                            \
    } while (0)

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // --- 1. 模块类型常量（纯逻辑，无硬件依赖） ---
    CHECK(QByteArray(QAccelerometer::type) == "QAccelerometer",
          "QAccelerometer::type constant");
    CHECK(QByteArray(QCompass::type) == "QCompass",
          "QCompass::type constant");

    // --- 2. 消费者侧传感器对象状态机（未连接后端时的确定性行为） ---
    QAccelerometer accelerometer;
    CHECK(!accelerometer.isActive(), "sensor inactive before start");
    accelerometer.setDataRate(50);
    CHECK(accelerometer.dataRate() == 50, "dataRate roundtrip");
    accelerometer.setAlwaysOn(true);
    CHECK(accelerometer.isAlwaysOn(), "alwaysOn roundtrip");
    accelerometer.setSkipDuplicates(true);
    CHECK(accelerometer.skipDuplicates(), "skipDuplicates roundtrip");
    CHECK(accelerometer.reading() == nullptr, "reading null before start");
    CHECK(!accelerometer.isConnectedToBackend(), "not connected to backend");
    QSensor &asSensor = accelerometer;
    CHECK(asSensor.type() == QByteArray(QAccelerometer::type),
          "QSensor::type() matches");

    // --- 3. 软件手势识别插件（纯软件识别器，无需传感器硬件） ---
    QSensorGestureManager gestureManager;
    QStringList gestureIds = gestureManager.gestureIds();
    CHECK(gestureIds.contains("QtSensors.shake"),
          "gesture plugin loaded (QtSensors.shake registered)");
    CHECK(!gestureIds.isEmpty(), "gesture ids non-empty");

    // --- 4. QML 模块导入与对象创建（QML 插件 + C++ 库链接完整性） ---
    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData("import QtSensors 5.0\nAccelerometer {\n}\n", QUrl());
    CHECK(!component.isError(), "QML import QtSensors without error");
    QObject *qmlSensor = component.create();
    CHECK(qmlSensor != nullptr, "QML Accelerometer object created");
    if (qmlSensor) {
        CHECK(qmlSensor->property("connectedToBackend").isValid()
              && !qmlSensor->property("connectedToBackend").toBool(),
              "QML connectedToBackend property (unconnected)");
        CHECK(qmlSensor->property("dataRate").isValid(),
              "QML dataRate property exposed");
        delete qmlSensor;
    }

    std::printf("Totals: %d checks, %d failed\n", 15, g_failures);
    return g_failures == 0 ? 0 : 1;
}
