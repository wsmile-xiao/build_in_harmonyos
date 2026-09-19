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

// kgoldrunner is an application package: the R34-relevant consumer
// verification is (a) executing the installed kgoldrunner binary and
// checking its --version output, and (b) parsing the gamedata files the
// package installs (share/kgoldrunner/system/game_*.txt) against the
// upstream KGoldrunner text format contract as implemented by
// src/kgrgameio.cpp:
//   * a game file starts with a G-header line ("// G018 K kgr N": id,
//     rules char, prefix, skill char),
//   * each level is a "// L###" marker line followed by ONE grid row line
//     (28+ characters, one char per cell) and i18n hint lines,
//   * game_ende.txt is the special "Ende screen" (no G-header, only L000)
//     and is skipped by upstream fetchGameListData.

static const int FIELD_WIDTH = 28;   // kgrglobals.h FIELDWIDTH

struct GameHeader {
    QString prefix;
    int nLevels;
    int rules;
};

static bool parseGameFile(const QString &path, GameHeader *out,
                          int *levelMarkers, int *gridRows,
                          int *firstLevelWidth)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) {
        return false;
    }
    const QList<QByteArray> lines = f.readAll().split('\n');

    bool haveHeader = false;
    int markers = 0;
    int grids = 0;
    int firstWidth = -1;
    bool expectGrid = false;
    int currentLevel = 0;

    for (const QByteArray &rawLine : lines) {
        QByteArray line = rawLine;
        if (line.endsWith('\r')) {
            line.chop(1);
        }
        if (!line.startsWith("// ")) {
            continue;
        }
        const QByteArray body = line.mid(3).trimmed();
        const QList<QByteArray> fields = body.split(' ');
        // level marker: "// L001" (3 digits)
        if (!fields.isEmpty() && fields.at(0).size() == 4
            && fields.at(0).at(0) == 'L'
            && fields.at(0).at(1) >= '0' && fields.at(0).at(1) <= '9'
            && fields.at(0).at(2) >= '0' && fields.at(0).at(2) <= '9'
            && fields.at(0).at(3) >= '0' && fields.at(0).at(3) <= '9') {
            markers++;
            currentLevel++;
            expectGrid = true;
            continue;
        }
        if (!haveHeader && !fields.isEmpty() && fields.at(0).startsWith('G')
            && fields.size() >= 4 && fields.at(0).size() == 4) {
            // "// G018 K kgr N" -> rules field 2, prefix field 3
            out->rules = fields.at(1).at(0);
            out->prefix = QString::fromUtf8(fields.at(2));
            out->nLevels = 0;
            haveHeader = true;
            continue;
        }
        if (expectGrid) {
            // attribute lines ("// .dwf true" — KGr2 downloadable flag and
            // friends) come between the level marker and the grid row;
            // skip them (upstream getALige treats '.'-prefixed lines as
            // attributes, never as grid rows).
            if (!fields.isEmpty() && fields.at(0).startsWith('.')) {
                continue;
            }
            // the first "// "-prefixed non-attribute line after a level
            // marker is the grid row for that level (one char per cell)
            if (body.size() < FIELD_WIDTH) {
                return false;
            }
            grids++;
            if (currentLevel == 1) {
                firstWidth = body.size();
            }
            expectGrid = false;
        }
    }
    *levelMarkers = markers;
    *gridRows = grids;
    *firstLevelWidth = firstWidth;
    return haveHeader && markers > 0;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ── Part 1: run the installed kgoldrunner binary (R34: real use of
    //    the tested package's deliverable). --version exits 0 and prints
    //    the version; requires offscreen platform on the OHOS worker.
    const QString exe = QString::fromUtf8(::getenv("KGR_TEST_BIN"));
    if (exe.isEmpty()) {
        printf("KGR_TEST_BIN not set\n");
        return 1;
    }
    if (!QFileInfo(exe).isExecutable()) {
        printf("installed kgoldrunner binary missing: %s\n", qPrintable(exe));
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
    if (prc != 0 || !versionOut.contains("kgoldrunner")
        || !versionOut.contains("26.04")) {
        printf("kgoldrunner --version failed (rc=%d): %s\n",
               prc, versionOut.constData());
        return 1;
    }
    printf("kgoldrunner --version OK: %s\n",
           versionOut.trimmed().constData());

    // ── Part 2: parse the installed gamedata files (the package ships
    //    share/kgoldrunner/system/game_*.txt with hundreds of levels).
    const QString dataDir = QString::fromUtf8(::getenv("KGR_TEST_DATA_DIR"));
    if (dataDir.isEmpty()) {
        printf("KGR_TEST_DATA_DIR not set\n");
        return 1;
    }
    QDir gamesDir(dataDir);
    if (!gamesDir.exists()) {
        printf("gamedata dir missing: %s\n", qPrintable(dataDir));
        return 1;
    }
    const QFileInfoList entries =
        gamesDir.entryInfoList(QStringList() << QStringLiteral("game_*.txt"),
                               QDir::Files, QDir::Name);
    if (entries.isEmpty()) {
        printf("no game_*.txt files in %s\n", qPrintable(dataDir));
        return 1;
    }
    // game_ende.txt is the special "Ende screen" file: upstream
    // kgrgameio.cpp fetchGameListData() skips it (no G-header, only L000).
    QList<QFileInfo> games;
    for (const QFileInfo &e : entries) {
        if (e.fileName() != QStringLiteral("game_ende.txt")) {
            games.append(e);
        }
    }
    if (games.isEmpty()) {
        printf("no playable game files\n");
        return 1;
    }

    int totalLevels = 0;
    int filesVerified = 0;
    int firstLevelWidth = -1;
    for (const QFileInfo &e : games) {
        GameHeader h;
        int markers = 0;
        int grids = 0;
        int width = -1;
        if (!parseGameFile(e.absoluteFilePath(), &h, &markers, &grids,
                           &width)) {
            printf("failed to parse %s\n", qPrintable(e.fileName()));
            return 1;
        }
        if (markers != grids) {
            printf("level markers (%d) != grid rows (%d) in %s\n",
                   markers, grids, qPrintable(e.fileName()));
            return 1;
        }
        totalLevels += markers;
        filesVerified++;
        if (width > 0 && firstLevelWidth < 0) {
            firstLevelWidth = width;
        }
    }
    if (totalLevels < 100) {
        printf("suspiciously few levels: %d\n", totalLevels);
        return 1;
    }
    if (firstLevelWidth < FIELD_WIDTH) {
        printf("first level width %d below minimum %d\n",
               firstLevelWidth, FIELD_WIDTH);
        return 1;
    }

    printf("kgoldrunner consumer test OK: binary --version verified, "
           "%d game files parsed, %d levels total, first level row %d "
           "columns (>= %d)\n",
           filesVerified, totalLevels, firstLevelWidth, FIELD_WIDTH);
    return 0;
}
