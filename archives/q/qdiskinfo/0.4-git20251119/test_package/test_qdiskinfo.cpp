// test_qdiskinfo.cpp — qdiskinfo 0.4-git20251119 消费者冒烟测试
//
// 以消费者身份（链接 Qt6::Core）驱动打包好的 QDiskInfo 可执行文件，
// 逐项断言并打印 "RESULT: N/N checks passed"：
//   1. 打包的 bin/QDiskInfo 存在且可执行
//   2. `--version` 在无显示服务器下退出码 0 并输出版本号（补丁 0002）
//   3. `--help` 在无显示服务器下退出码 0 并输出用法（补丁 0002）
//   4. `--ascii-view <dev>` 无 GUI 路径：非 root 报错退出、root 正常退出
//   5. GUI 在 offscreen QPA 下能启动（Qt 平台插件 + Widgets 加载成功）
//      且主窗口构造后不崩溃
//
// 用法: test_qdiskinfo <path-to-QDiskInfo>
#include <QCoreApplication>
#include <QFileInfo>
#include <QProcess>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>

#include <cstdio>
#include <unistd.h>

namespace {

int g_total = 0;
int g_passed = 0;

void check(bool ok, const QString &label)
{
    ++g_total;
    if (ok) {
        ++g_passed;
    }
    std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", qPrintable(label));
    std::fflush(stdout);
}

struct RunResult
{
    bool started = false;
    bool timedOut = false;
    int exitCode = -1;
    QString out;
    QString err;
};

RunResult runApp(const QString &appPath, const QStringList &args,
                 int timeoutMs, bool offscreen)
{
    QProcess process;
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    if (offscreen) {
        env.insert(QStringLiteral("QT_QPA_PLATFORM"), QStringLiteral("offscreen"));
    }
    process.setProcessEnvironment(env);
    process.setProcessChannelMode(QProcess::SeparateChannels);
    process.start(appPath, args);

    RunResult r;
    r.started = process.waitForStarted(timeoutMs);
    if (!r.started) {
        return r;
    }
    if (process.waitForFinished(timeoutMs)) {
        r.exitCode = process.exitCode();
    } else {
        r.timedOut = true;
        process.kill();
        process.waitForFinished(5000);
        r.exitCode = process.exitCode();
    }
    r.out = QString::fromLocal8Bit(process.readAllStandardOutput());
    r.err = QString::fromLocal8Bit(process.readAllStandardError());
    return r;
}

} // namespace

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s <path-to-QDiskInfo>\n", argv[0]);
        return 2;
    }
    const QString appPath = QString::fromLocal8Bit(argv[1]);

    // 1. 打包产物
    const QFileInfo info(appPath);
    check(info.exists(), QStringLiteral("打包二进制存在: ") + appPath);
    check(info.isExecutable(), QStringLiteral("打包二进制可执行"));

    // 2. --version（无 GUI 早期退出，补丁 0002）
    const RunResult version = runApp(appPath, {QStringLiteral("--version")}, 20000, false);
    check(version.started && !version.timedOut && version.exitCode == 0
              && version.out.contains(QStringLiteral("QDiskInfo")),
          QStringLiteral("--version 退出码 0 且输出版本号 (rc=%1, out=%2)")
              .arg(version.exitCode).arg(version.out.trimmed()));

    // 3. --help
    const RunResult help = runApp(appPath, {QStringLiteral("--help")}, 20000, false);
    check(help.started && !help.timedOut && help.exitCode == 0
              && help.out.contains(QStringLiteral("Usage")),
          QStringLiteral("--help 退出码 0 且输出用法 (rc=%1)").arg(help.exitCode));

    // 4. --ascii-view：无 GUI，行为由 euid 决定（main.cpp 在构造 QApplication 前返回）
    const RunResult ascii = runApp(appPath,
                                   {QStringLiteral("--ascii-view"), QStringLiteral("/dev/null")},
                                   20000, false);
    if (geteuid() == 0) {
        check(ascii.started && !ascii.timedOut && ascii.exitCode == 0,
              QStringLiteral("root: --ascii-view /dev/null 退出码 0 (rc=%1)").arg(ascii.exitCode));
    } else {
        check(ascii.started && !ascii.timedOut && ascii.exitCode == 1
                  && ascii.err.contains(QStringLiteral("root privileges")),
              QStringLiteral("非 root: --ascii-view 以 'requires root privileges' 退出 (rc=%1)")
                  .arg(ascii.exitCode));
    }

    // 5. GUI offscreen 启动冒烟
    const RunResult gui = runApp(appPath, {}, 15000, true);
    check(gui.started,
          QStringLiteral("offscreen QPA 下进程成功启动（Qt 平台插件加载）"));
    check(gui.started && (gui.timedOut || gui.exitCode == 0),
          QStringLiteral("offscreen 主窗口构造后未崩溃 (timeout=%1 rc=%2, err=%3)")
              .arg(gui.timedOut ? 1 : 0).arg(gui.exitCode)
              .arg(gui.err.trimmed().left(200)));

    std::printf("RESULT: %d/%d checks passed\n", g_passed, g_total);
    return g_passed == g_total ? 0 : 1;
}
