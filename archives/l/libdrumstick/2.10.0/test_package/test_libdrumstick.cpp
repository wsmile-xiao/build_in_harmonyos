// test_libdrumstick.cpp — 消费者视角验证 libdrumstick 2.10.0 真实 API。
// 链接 Drumstick::File 与 Drumstick::RT：
//   1) drumstick::File::QSmf 写/读 SMF 数据流；
//   2) drumstick::rt::BackendManager 枚举已安装 RT 后端插件。
// 用法参照上游 tests/fileTest1/filetest1.cpp（QByteArray + QDataStream）。
#include <QByteArray>
#include <QCoreApplication>
#include <QDataStream>
#include <QDebug>
#include <QIODevice>
#include <QSettings>
#include <QStringList>

#include <drumstick/backendmanager.h>
#include <drumstick/qsmf.h>

using namespace drumstick::File;
namespace rt = drumstick::rt;

static int test_smf_roundtrip()
{
    // 构造一个最小 SMF（division=480，format 1，2 轨）写入流再读回
    QByteArray data;
    QDataStream out(&data, QIODevice::ReadWrite);
    QSmf writer;
    writer.setFileFormat(1);
    writer.setTracks(2);
    writer.setDivision(480);
    writer.writeToStream(&out);

    QDataStream in(&data, QIODevice::ReadOnly);
    QSmf reader;
    reader.readFromStream(&in);
    if (reader.getFileFormat() != 1) {
        qWarning() << "file format mismatch:" << reader.getFileFormat();
        return 1;
    }
    if (reader.getTracks() != 2) {
        qWarning() << "tracks mismatch:" << reader.getTracks();
        return 2;
    }
    if (reader.getDivision() != 480) {
        qWarning() << "division mismatch:" << reader.getDivision();
        return 3;
    }
    return 0;
}

static int test_backend_manager()
{
    rt::BackendManager manager;
    QSettings settings;
    manager.refresh(&settings);
    QStringList paths = manager.defaultPaths();
    if (paths.isEmpty()) {
        qWarning() << "no backend plugin paths found";
        return 4;
    }
    // 安装包应至少能枚举到 OSS/Network/FluidSynth 后端之一
    QList<rt::MIDIInput *> inputs = manager.availableInputs();
    QList<rt::MIDIOutput *> outputs = manager.availableOutputs();
    if (inputs.isEmpty() && outputs.isEmpty()) {
        qWarning() << "no RT backends enumerated";
        return 5;
    }
    return 0;
}

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    // 默认分支同样执行全部真实测试（SMF 往返 + 后端枚举），
    // 避免直接运行二进制时跳过测试却返回 0。
    Q_UNUSED(app);
    int rc = test_smf_roundtrip();
    if (rc != 0) {
        return rc;
    }
    rc = test_backend_manager();
    if (rc != 0) {
        return rc;
    }
    qInfo() << "libdrumstick test_package: OK";
    return 0;
}
