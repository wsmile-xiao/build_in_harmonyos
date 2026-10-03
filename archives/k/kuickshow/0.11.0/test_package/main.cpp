#include <QByteArray>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QFileInfoList>
#include <QList>
#include <QString>
#include <QStringList>
#include <cstdio>
#include <cstdlib>

// kuickshow is an application package (upstream registers no test suite,
// N=0 — grep evidence in MANIFEST.yml). The consumer verification covers:
//
//  Part 1 (R34): execute the installed kuickshow binary with --version
//    under QT_QPA_PLATFORM=offscreen and assert the 0.11.0 version string
//    (QCommandLineParser::process exits 0 inside main() before any window
//    or KXMLGUIClient is constructed).
//  Part 2: the Imlib palette data contract — misc/im_palette.pal is
//    installed to share/kuickshow/im_palette.pal; every non-empty line is
//    three whitespace-separated "0xRR GG BB" hex fields (64 lines in the
//    upstream file; the pure-Qt backend does not read it but the packaged
//    data artifact must still match the upstream format the Imlib1
//    backend consumes — src/imlib_imlib1.cpp reads "0xR 0xG 0xB" lines).
//  Part 3: the application data contract — share/kuickshow/pics/ carries
//    the 9 files from pics/CMakeLists.txt (calibrate.png kuickshow-day.jpg
//    kuickshow-night.jpg logo.png imageviewer-medium.png
//    imageviewer-small.png handcursor.png ksslide.png about.png).
//  Part 4: the desktop integration contract — share/applications/
//    org.kde.kuickshow.desktop (Exec=kuickshow, Type=Application,
//    Icon=kuickshow), hicolor icons for 16/22/32 px, and the
//    share/qlogging-categories/kuickshow.categories logging categories
//    file (ecm_qt_install_logging_categories EXPORT kuickshow).

static bool isHexField(const QByteArray &f)
{
    if (f.size() < 3 || !f.startsWith("0x")) {
        return false;
    }
    for (int i = 2; i < f.size(); ++i) {
        const char c = f.at(i);
        const bool ok = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')
                        || (c >= 'A' && c <= 'F');
        if (!ok) {
            return false;
        }
    }
    return true;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ── Part 1: run the installed kuickshow binary (R34).
    const QString exe = QString::fromUtf8(::getenv("KS_TEST_BIN"));
    if (exe.isEmpty()) {
        printf("KS_TEST_BIN not set\n");
        return 1;
    }
    if (!QFileInfo(exe).isExecutable()) {
        printf("installed kuickshow binary missing: %s\n", qPrintable(exe));
        return 1;
    }
    QString cmd = exe + QStringLiteral(" --version 2>&1");
    FILE *p = ::popen(cmd.toUtf8().constData(), "r");
    if (!p) {
        printf("popen failed\n");
        return 1;
    }
    QByteArray versionOut;
    char buf[512];
    while (::fgets(buf, sizeof buf, p)) {
        versionOut += buf;
    }
    const int prc = ::pclose(p);
    if (prc != 0 || !versionOut.contains("kuickshow")
        || !versionOut.contains("0.11.0")) {
        printf("kuickshow --version failed (rc=%d): %s\n",
               prc, versionOut.constData());
        return 1;
    }
    printf("kuickshow --version OK: %s\n",
           versionOut.trimmed().constData());

    // ── Part 2: the Imlib palette contract.
    const QString dataDir = QString::fromUtf8(::getenv("KS_TEST_DATA_DIR"));
    if (dataDir.isEmpty()) {
        printf("KS_TEST_DATA_DIR not set\n");
        return 1;
    }
    const QString palette = dataDir + QStringLiteral("/im_palette.pal");
    QFile pal(palette);
    if (!pal.open(QIODevice::ReadOnly | QIODevice::Text)) {
        printf("palette missing: %s\n", qPrintable(palette));
        return 1;
    }
    int palLines = 0;
    int palBad = 0;
    while (!pal.atEnd()) {
        const QByteArray raw = pal.readLine();
        const QByteArray line = raw.trimmed();
        if (line.isEmpty()) {
            continue;
        }
        ++palLines;
        const QList<QByteArray> fields = line.split(' ');
        if (fields.size() != 3 || !isHexField(fields.at(0))
            || !isHexField(fields.at(1)) || !isHexField(fields.at(2))) {
            ++palBad;
        }
    }
    if (palBad || palLines != 64) {
        printf("palette contract violated: %d lines, %d malformed\n",
               palLines, palBad);
        return 1;
    }
    printf("palette OK: %d lines, all \"0xR 0xG 0xB\" triplets\n", palLines);

    // ── Part 3: the application data contract.
    const QDir pics(dataDir + QStringLiteral("/pics"));
    const QStringList expectedPics = {
        QStringLiteral("calibrate.png"),
        QStringLiteral("kuickshow-day.jpg"),
        QStringLiteral("kuickshow-night.jpg"),
        QStringLiteral("logo.png"),
        QStringLiteral("imageviewer-medium.png"),
        QStringLiteral("imageviewer-small.png"),
        QStringLiteral("handcursor.png"),
        QStringLiteral("ksslide.png"),
        QStringLiteral("about.png"),
    };
    if (!pics.exists()) {
        printf("pics dir missing: %s\n", qPrintable(pics.absolutePath()));
        return 1;
    }
    for (const QString &name : expectedPics) {
        if (!pics.exists(name)) {
            printf("packaged pic missing: %s\n", qPrintable(name));
            return 1;
        }
    }
    printf("pics OK: %d files present\n", expectedPics.size());

    // ── Part 4: the desktop integration contract.
    const QString baseDir =
        QString::fromUtf8(::getenv("KS_TEST_PREFIX"));
    if (baseDir.isEmpty()) {
        printf("KS_TEST_PREFIX not set\n");
        return 1;
    }
    const QString desktop = baseDir
        + QStringLiteral("/share/applications/org.kde.kuickshow.desktop");
    QFile df(desktop);
    if (!df.open(QIODevice::ReadOnly | QIODevice::Text)) {
        printf("desktop entry missing: %s\n", qPrintable(desktop));
        return 1;
    }
    QByteArray dcontent = df.readAll();
    if (!dcontent.contains("Exec=kuickshow")
        || !dcontent.contains("Type=Application")
        || !dcontent.contains("Icon=kuickshow")) {
        printf("desktop entry contract violated\n");
        return 1;
    }
    const QDir icons(baseDir + QStringLiteral("/share/icons/hicolor"));
    if (!icons.exists()) {
        printf("hicolor icons dir missing\n");
        return 1;
    }
    int iconCount = 0;
    const QFileInfoList iconEntries =
        icons.entryInfoList(QStringList() << QStringLiteral("kuickshow.png"),
                            QDir::Files, QDir::Name);
    // entryInfoList is non-recursive: walk the size dirs explicitly.
    const QFileInfoList sizeDirs =
        icons.entryInfoList(QStringList(), QDir::Dirs | QDir::NoDotAndDotDot);
    for (const QFileInfo &sd : sizeDirs) {
        QDir appDir(sd.absoluteFilePath() + QStringLiteral("/apps"));
        if (appDir.exists(QStringLiteral("kuickshow.png"))) {
            ++iconCount;
        }
    }
    if (iconCount < 3) {
        printf("expected 3+ hicolor kuickshow.png icons, found %d\n",
               iconCount);
        return 1;
    }
    const QString cats = baseDir
        + QStringLiteral("/share/qlogging-categories6/kuickshow.categories");
    if (!QFileInfo::exists(cats)) {
        printf("logging categories file missing: %s\n", qPrintable(cats));
        return 1;
    }

    printf("kuickshow consumer test OK: --version verified, palette 64 "
           "triplets, %d pics, desktop entry + %d icons + categories\n",
           expectedPics.size(), iconCount);
    return 0;
}
