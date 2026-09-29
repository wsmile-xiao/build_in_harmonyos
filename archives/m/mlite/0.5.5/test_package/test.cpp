// mlite/0.5.5 消费方测试（test_package）
//
// 用例：
//   1. desktopEntryParser    —— MDesktopEntry 解析 .desktop（包公共 API，不依赖 D-Bus）
//   2. remoteActionRoundTrip —— MRemoteAction toString() 往返（包公共 API，不依赖 D-Bus 连接）
//   3. ohosSharedLibraryElf  —— 鸿蒙特有用例：校验本包 .so 被 OHOS 加载器接受、ELF 目标标记为 OHOS/aarch64
//
// 说明：本构型为上游原生「dconf 关闭」构型（src/src.pro 的 packagesExist(dconf) 为假），
// MDConf*/MGConfItem 系列不参与构建，故测试只覆盖其余公共 API。
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QStringList>
#include <QVariant>

#include <MDesktopEntry>
#include <MRemoteAction>

#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <link.h>

#ifndef EM_AARCH64
#define EM_AARCH64 183
#endif

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const char *what)
{
    ++g_checks;
    if (ok) {
        std::printf("PASS: %s\n", what);
    } else {
        ++g_failures;
        std::printf("FAIL: %s\n", what);
    }
}

// ── 鸿蒙特有用例：定位已加载的 libmlite5.so.0 并校验其 ELF 目标标记 ──────────────
static int findMliteSo(struct dl_phdr_info *info, size_t, void *data)
{
    const char *name = info->dlpi_name;
    if (name && std::strstr(name, "libmlite5.so")) {
        *static_cast<QString *>(data) = QString::fromLocal8Bit(name);
        return 1;   // 停止遍历
    }
    return 0;
}

static void testOhosSharedLibraryElf()
{
#if defined(__OHOS__)
    QString loadedPath;
    dl_iterate_phdr(findMliteSo, &loadedPath);
    check(!loadedPath.isEmpty(),
          "OHOS: libmlite5.so.0 已被 OHOS 加载器加载（dl_iterate_phdr 可见）");
    if (loadedPath.isEmpty()) {
        return;
    }
    std::printf("INFO: loaded library = %s\n", qPrintable(loadedPath));

    QFile file(loadedPath);
    check(file.open(QIODevice::ReadOnly), "OHOS: 共享库文件可读");
    if (!file.isOpen()) {
        return;
    }
    const QByteArray head = file.read(4096);
    const bool elfMagic = head.size() > 64
            && static_cast<unsigned char>(head.at(0)) == 0x7f
            && head.at(1) == 'E' && head.at(2) == 'L' && head.at(3) == 'F';
    check(elfMagic, "OHOS: 产物为 ELF 文件");
    if (!elfMagic) {
        return;
    }
    const unsigned char *raw = reinterpret_cast<const unsigned char *>(head.constData());
    const unsigned int machine = raw[18] | (raw[19] << 8);
    std::printf("INFO: e_machine=%u (EM_AARCH64=%u)\n", machine, EM_AARCH64);
    check(machine == EM_AARCH64, "OHOS: ELF 目标架构为 aarch64");
    check(head.contains("OHOS"), "OHOS: ELF 含 OHOS 目标标记（.note.ohos.ident）");
#else
    std::printf("SKIP: OHOS 专有用例（当前平台非 OHOS）\n");
#endif
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ── 1) MDesktopEntry ────────────────────────────────────────────────
    const QString dir = QDir::tempPath() + QStringLiteral("/mlite-test-package");
    QDir().mkpath(dir);
    const QString path = dir + QStringLiteral("/mlite-smoke.desktop");
    {
        QFile file(path);
        if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
            std::printf("FAIL: 无法写入测试用 .desktop\n");
            return 1;
        }
        QTextStream out(&file);
        out << "[Desktop Entry]\n"
            << "Type=Application\n"
            << "Name=Foo\n"
            << "Exec=/bin/true\n"
            << "Icon=foo\n"
            << "X-Mlite-Smoke=1\n";
    }
    MDesktopEntry entry(path);
    check(entry.isValid(), "MDesktopEntry: .desktop 解析有效");
    check(entry.name() == QStringLiteral("Foo"), "MDesktopEntry: name() == Foo");
    check(entry.value(QStringLiteral("Type")) == QStringLiteral("Application"),
          "MDesktopEntry: value(Type) == Application");
    // contains(key) 需带组名前缀（上游 ut_mdesktopentry.cpp:205-217 的语义）：
    // 单 token 形式会按 '/' 切分并要求恰好 2 段，故此处用 Group/Key 与 (Group, Key) 两种写法
    check(entry.contains(QStringLiteral("Desktop Entry"), QStringLiteral("X-Mlite-Smoke")),
          "MDesktopEntry: contains(Desktop Entry, X-Mlite-Smoke)");
    check(entry.contains(QStringLiteral("Desktop Entry/X-Mlite-Smoke")),
          "MDesktopEntry: contains(Desktop Entry/X-Mlite-Smoke)");
    check(!entry.contains(QStringLiteral("Desktop Entry"), QStringLiteral("NoSuchKey")),
          "MDesktopEntry: !contains(Desktop Entry, NoSuchKey)");
    check(entry.value(QStringLiteral("X-Mlite-Smoke")) == QStringLiteral("1"),
          "MDesktopEntry: value(X-Mlite-Smoke) == 1");

    // ── 2) MRemoteAction（仅序列化往返，不建立 D-Bus 连接） ───────────────
    MRemoteAction original(QStringLiteral("org.example.Service"),
                           QStringLiteral("/org/example/Object"),
                           QStringLiteral("org.example.Interface"),
                           QStringLiteral("Baz"),
                           QVariantList() << 123 << QStringLiteral("abc")
                                          << (QStringList() << "a" << "b" << "c"));
    check(original.isValid(), "MRemoteAction: 构造有效");
    MRemoteAction restored(original.toString());
    check(original.toString() == restored.toString(), "MRemoteAction: toString() 往返一致");
    check(restored.serviceName() == original.serviceName(), "MRemoteAction: serviceName 保留");
    check(restored.objectPath() == original.objectPath(), "MRemoteAction: objectPath 保留");
    check(restored.methodName() == original.methodName(), "MRemoteAction: methodName 保留");

    // ── 3) OHOS 专有用例 ────────────────────────────────────────────────
    testOhosSharedLibraryElf();

    std::printf("SUMMARY: %d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
