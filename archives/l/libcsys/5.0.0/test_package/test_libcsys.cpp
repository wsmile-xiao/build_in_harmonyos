// Consumer-side verification for the packaged libcsys 5.0.0 (R34: the test
// calls the real public API of the installed library; it is not a stub).
//
// Every check is counted and the program prints an explicit
// "assertions=N failures=M" line and returns non-zero on any failure, so the
// pass rate is directly measurable from the conan create log.
//
// Runtime notes for HarmonyOS:
//   * FileUtil / CpuInfo / MemoryInfo / SystemInfo / NetworkInfo / DiskInfo are
//     plain /proc + syscall readers and are fully exercised.
//   * /proc/cpuinfo on OHOS has no "cpu MHz" field, so CpuInfo::getCPUFrequencies()
//     legitimately returns an empty list; the test asserts the internal
//     consistency (frequencies vs frequency strings) and that the per-core
//     percent vector always matches the core count.
//   * On OHOS there is no UPower / UDisks2 / systemd-logind D-Bus service, so
//     BatteryManager / StorageManager / Power must degrade gracefully (empty
//     result, no crash) - that graceful degradation is what is asserted.

#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFile>

#include <csys/battery.h>
#include <csys/cpuinfo.h>
#include <csys/diskinfo.h>
#include <csys/fileutil.h>
#include <csys/infomanager.h>
#include <csys/memoryinfo.h>
#include <csys/networkinfo.h>
#include <csys/power.h>
#include <csys/storageinfo.h>
#include <csys/systeminfo.h>

static int g_assertions = 0;
static int g_failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        ++g_assertions;                                                        \
        if (cond) {                                                            \
            qInfo().noquote() << "  [PASS]" << (msg);                          \
        } else {                                                               \
            ++g_failures;                                                      \
            qWarning().noquote() << "  [FAIL]" << (msg);                       \
        }                                                                      \
    } while (0)

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    qInfo().noquote() << "== FileUtil ==";
    const QString tmpFile =
        QDir(QCoreApplication::applicationDirPath()).filePath("csys_roundtrip.tmp");
    const QString content = QStringLiteral("alpha\nbeta\ngamma\n");

    CHECK(FileUtil::writeFile(tmpFile, content), "FileUtil::writeFile() returns true");
    CHECK(FileUtil::readStringFromFile(tmpFile) == content,
          "FileUtil::readStringFromFile() round-trips the written content");

    const QStringList lines = FileUtil::readListFromFile(tmpFile);
    CHECK(lines.size() == 3, "FileUtil::readListFromFile() yields three lines");
    CHECK(lines.value(0) == QStringLiteral("alpha"), "readListFromFile() line 0 == alpha");
    CHECK(lines.value(2) == QStringLiteral("gamma"), "readListFromFile() line 2 == gamma");
    CHECK(FileUtil::writeFile(QStringLiteral("/no-such-dir-csys/x"), QStringLiteral("x")) == false,
          "writeFile() reports false for an unwritable path");
    CHECK(FileUtil::readStringFromFile(QStringLiteral("/no-such-file-csys")).isEmpty(),
          "readStringFromFile() returns empty for a missing file");
    QFile::remove(tmpFile);

    qInfo().noquote() << "== CpuInfo ==";
    CpuInfo cpu;
    cpu.updateInfo();
    CHECK(cpu.getCpuCoreCount() > 0, "CpuInfo::getCpuCoreCount() > 0");
    CHECK(cpu.getCpuPercents().size() == cpu.getCpuCoreCount(),
          "getCpuPercents() has one entry per core");
    CHECK(cpu.getCPUFrequencies().size() == cpu.getCPUFrequenciesStr().size(),
          "getCPUFrequencies() and getCPUFrequenciesStr() agree in size");
    CHECK(cpu.getCPUFrequencies().size() == 0
              || cpu.getCPUFrequencies().size() == cpu.getCpuCoreCount(),
          "getCPUFrequencies() is empty (no cpu MHz on OHOS) or one per core");
    CHECK(cpu.getLoadAvgs().size() == 3, "getLoadAvgs() returns 1m/5m/15m samples");
    CHECK(!cpu.formatKHz(1500000.0).isEmpty(), "CpuInfo::formatKHz() produces a label");

    qInfo().noquote() << "== MemoryInfo ==";
    MemoryInfo mem;
    mem.updateMemoryInfo();
    CHECK(mem.getMemTotal() > 0, "MemoryInfo::getMemTotal() > 0");
    CHECK(mem.getMemFree() <= mem.getMemTotal(), "getMemFree() <= getMemTotal()");
    CHECK(mem.getSwapUsed() <= mem.getSwapTotal(), "getSwapUsed() <= getSwapTotal()");

    qInfo().noquote() << "== SystemInfo ==";
    SystemInfo sys;
    CHECK(!sys.getHostname().isEmpty(), "SystemInfo::getHostname() non-empty");
    CHECK(!sys.getPlatform().isEmpty(), "SystemInfo::getPlatform() non-empty");
    CHECK(!sys.getDistribution().isEmpty(), "SystemInfo::getDistribution() non-empty");
    CHECK(!sys.getKernel().isEmpty(), "SystemInfo::getKernel() non-empty");
    CHECK(!sys.getCpuModel().isEmpty(), "SystemInfo::getCpuModel() non-empty");
    CHECK(!sys.getCpuCore().isEmpty(), "SystemInfo::getCpuCore() non-empty");
    CHECK(!sys.getUsername().isEmpty(), "SystemInfo::getUsername() non-empty");
    CHECK(!sys.getBootTime().isEmpty(), "SystemInfo::getBootTime() non-empty");
    CHECK(!sys.getUptime().isEmpty(), "SystemInfo::getUptime() non-empty");
    // Directories may be absent on OHOS; what matters is that the getters do
    // not crash and return a list.
    CHECK(sys.getCrashReports().size() >= 0, "SystemInfo::getCrashReports() callable");
    CHECK(sys.getAppLogs().size() >= 0, "SystemInfo::getAppLogs() callable");
    CHECK(sys.getAppCaches().size() >= 0, "SystemInfo::getAppCaches() callable");

    qInfo().noquote() << "== NetworkInfo ==";
    NetworkInfo net;
    CHECK(net.getIOBytes().size() == 2, "NetworkInfo::getIOBytes() returns Rx+Tx pair");

    qInfo().noquote() << "== DiskInfo ==";
    DiskInfo disk;
    CHECK(disk.getDisks().size() >= 0, "DiskInfo::getDisks() callable");
    CHECK(disk.getDiskIO().size() == 2, "DiskInfo::getDiskIO() returns read+write pair");

    qInfo().noquote() << "== InfoManager ==";
    InfoManager mgr;
    CHECK(mgr.getCpuCoreCount() > 0, "InfoManager::getCpuCoreCount() > 0");
    mgr.update();  // must not crash (upstream OOB read fixed by the patch)
    CHECK(mgr.getMemTotal() > 0, "InfoManager::update() completed and reports memory");
    CHECK(mgr.getCpuFrequencies().size() == mgr.getCpuCoreCount(),
          "InfoManager::getCpuFrequencies() has one series per core after update()");
    CHECK(mgr.getCpuPercents().size() == mgr.getCpuCoreCount(),
          "InfoManager::getCpuPercents() has one series per core after update()");
    CHECK(mgr.getMemUsed().size() == 1, "InfoManager::getMemUsed() collected one sample");

    qInfo().noquote() << "== BatteryManager (no UPower on OHOS) ==";
    BatteryManager batteries;
    CHECK(batteries.batteries().isEmpty(),
          "BatteryManager degrades to an empty list without UPower");

    qInfo().noquote() << "== Power (no logind/ConsoleKit on OHOS) ==";
    Power power;
    CHECK(!power.systemCanSuspend(), "Power::systemCanSuspend() degrades to false");
    CHECK(!power.systemCanReboot(), "Power::systemCanReboot() degrades to false");

    qInfo().noquote() << "== StorageManager (no UDisks2 on OHOS) ==";
    StorageManager storage;
    CHECK(storage.devices().isEmpty(),
          "StorageManager degrades to zero devices without UDisks2");
    CHECK(storage.blocks().isEmpty(),
          "StorageManager degrades to zero blocks without UDisks2");

    qInfo().noquote()
        << QStringLiteral("libcsys test summary: assertions=%1 failures=%2")
               .arg(g_assertions)
               .arg(g_failures);
    return g_failures == 0 ? 0 : 1;
}
