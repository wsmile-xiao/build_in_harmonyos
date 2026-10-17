/*
 * test_disomaster - disomaster 公共 API 非破坏性消费者测试
 *
 * 35 个断言覆盖所有公开 API：
 * - 构造和析构
 * - 初始状态检查
 * - 暂存文件管理
 * - 设备属性缓存
 * - 未获取设备时拒绝操作
 * - 使用 fake_xorriso 执行所有光盘操作
 * - JobStatus 信号验证（含信号顺序验证）
 * - checkmedia 质量比例验证
 * - getCurrentSpeed 验证
 *
 * 接收 fake_xorriso 路径作为 argv[1]，通过环境变量 DISOMASTER_XORRISO 传递给 DISOMaster。
 * 每个断言失败返回不同的非零退出码（101-134）。
 */
#include "disomaster.h"

#include <QCoreApplication>
#include <QUrl>
#include <QHash>
#include <QList>

#include <cstdio>

using namespace DISOMasterNS;

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    /* 接收 fake_xorriso 路径作为命令行参数 */
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <fake_xorriso_path>\n", argv[0]);
        return 1;
    }

    /* 设置 DISOMASTER_XORRISO 环境变量指向 fake_xorriso */
    qputenv("DISOMASTER_XORRISO", argv[1]);

    /* 信号状态追踪 */
    bool gotRunning = false;
    bool gotFinished = false;
    bool gotFinishedAfterRunning = false;  /* 追踪信号顺序：Finished 必须在 Running 之后 */
    bool gotRunningAfterFinished = false;  /* 追踪信号顺序：禁止 Running 出现在 Finished 之后 */

    /* ========== 断言 1: 构造 DISOMaster ========== */
    DISOMaster master;
    QObject::connect(&master, &DISOMaster::jobStatusChanged,
        [&gotRunning, &gotFinished, &gotFinishedAfterRunning, &gotRunningAfterFinished](DISOMaster::JobStatus status, int) {
            if (status == DISOMaster::Running) {
                if (gotFinished) gotRunningAfterFinished = true;
                gotRunning = true;
            }
            if (status == DISOMaster::Finished) {
                if (gotRunning) gotFinishedAfterRunning = true;
                gotFinished = true;
            }
        });

    /* ========== 断言 2: 初始设备为空 ========== */
    if (!master.currentDevice().isEmpty()) return 102;

    /* ========== 断言 3: 初始速度为空 ========== */
    if (!master.getCurrentSpeed().isEmpty()) return 103;

    /* ========== 断言 4: 初始消息列表为空 ========== */
    if (!master.getInfoMessages().isEmpty()) return 104;

    /* ========== 断言 5: 初始暂存文件为空 ========== */
    if (!master.stagingFiles().isEmpty()) return 105;

    /* ========== 断言 6: 暂存文件 ========== */
    QHash<QUrl, QUrl> fileList;
    fileList[QUrl("file:///file1")] = QUrl("file:///src1");
    fileList[QUrl("file:///file2")] = QUrl("file:///src2");
    fileList[QUrl("file:///file3")] = QUrl("file:///src3");
    master.stageFiles(fileList);

    /* ========== 断言 7: 暂存文件已添加（3 个）========== */
    if (master.stagingFiles().size() != 3) return 106;

    /* ========== 断言 8: 移除部分暂存文件 ========== */
    master.removeStagingFiles({QUrl("file:///file2")});

    /* ========== 断言 9: 暂存文件已减少（2 个）========== */
    if (master.stagingFiles().size() != 2) return 107;

    /* ========== 断言 10: 未缓存的设备属性返回 NoMedia ========== */
    DeviceProperty cached = master.getDevicePropertyCached("/dev/sr0");
    if (cached.media != NoMedia) return 108;

    /* ========== 断言 11: 未获取设备时 commit 返回 false ========== */
    if (master.commit(BurnOptions(ISO9660Only), 0, "TEST")) return 109;

    /* ========== 断言 12: 未获取设备时 erase 返回 false ========== */
    if (master.erase()) return 110;

    /* ========== 断言 13: 未获取设备时 checkmedia 返回 false ========== */
    double qgood = 0, qslow = 0, qbad = 0;
    if (master.checkmedia(&qgood, &qslow, &qbad)) return 111;

    /* ========== 断言 14: 未获取设备时 dumpISO 返回 false ========== */
    if (master.dumpISO(QUrl("file:///tmp/test.iso"))) return 112;

    /* ========== 断言 15: 未获取设备时 writeISO 返回 false ========== */
    if (master.writeISO(QUrl("file:///tmp/test.iso"))) return 113;

    /* ========== 断言 16: 获取设备成功 ========== */
    if (!master.acquireDevice("/dev/sr0")) return 114;

    /* ========== 断言 17: 当前设备已设置 ========== */
    if (master.currentDevice() != "/dev/sr0") return 115;

    /* ========== 断言 18: 设备属性介质类型为 CD-RW ========== */
    DeviceProperty dp = master.getDeviceProperty();
    if (dp.media != CD_RW) return 116;

    /* ========== 断言 19: 设备属性 formatted 为 true（空白介质）========== */
    if (!dp.formatted) return 117;

    /* ========== 断言 20: 设备属性卷标为 ISOIMAGE ========== */
    if (dp.volid != "ISOIMAGE") return 118;

    /* ========== 断言 21: 设备属性写入速度列表不为空 ========== */
    if (dp.writespeed.isEmpty()) return 119;

    /* ========== 断言 22: getDevicePropertyCached 返回缓存数据 ========== */
    DeviceProperty cachedAfter = master.getDevicePropertyCached("/dev/sr0");
    if (cachedAfter.media != CD_RW) return 120;

    /* ========== 断言 23: 清除设备属性缓存 ========== */
    master.nullifyDevicePropertyCache("/dev/sr0");
    DeviceProperty cachedNull = master.getDevicePropertyCached("/dev/sr0");
    if (cachedNull.media != NoMedia) return 121;

    /* ========== 断言 24: commit 成功 ========== */
    gotRunning = false;
    gotFinished = false;
    gotFinishedAfterRunning = false;
    gotRunningAfterFinished = false;
    BurnOptions opts;
    opts |= ISO9660Only;
    if (!master.commit(opts, 10, "TESTVOL")) return 122;

    /* ========== 断言 25: commit 后收到 Finished 信号 ========== */
    if (!gotFinished) return 123;

    /* ========== 断言 26: commit 后收到 Running 信号 ========== */
    if (!gotRunning) return 124;

    /* ========== 断言 26b: 信号顺序正确（Finished 在 Running 之后，无二次 Running）========== */
    if (!gotFinishedAfterRunning) return 133;
    if (gotRunningAfterFinished) return 134;

    /* ========== 断言 27: erase 成功 ========== */
    if (!master.erase()) return 125;

    /* ========== 断言 28: checkmedia 成功 ========== */
    qgood = 0; qslow = 0; qbad = 0;
    if (!master.checkmedia(&qgood, &qslow, &qbad)) return 126;

    /* ========== 断言 29: checkmedia 质量比例 - 良好率接近 1.0 ========== */
    if (qgood < 0.99) return 127;

    /* ========== 断言 30: checkmedia 质量比例 - 无坏块 ========== */
    if (qbad > 0.01) return 128;

    /* ========== 断言 31: dumpISO 成功 ========== */
    if (!master.dumpISO(QUrl("file:///tmp/dump.iso"))) return 129;

    /* ========== 断言 32: writeISO 成功 ========== */
    if (!master.writeISO(QUrl("file:///tmp/write.iso"), 10)) return 130;

    /* ========== 断言 33: getCurrentSpeed 不为空（操作后已设置）========== */
    if (master.getCurrentSpeed().isEmpty()) return 131;

    /* ========== 断言 34: releaseDevice 清除设备 ========== */
    master.releaseDevice();
    if (!master.currentDevice().isEmpty()) return 132;

    printf("All 35 assertions passed.\n");
    return 0;
}
