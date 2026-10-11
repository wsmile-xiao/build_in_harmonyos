/*
   Consumer smoke test for qmmp 2.3.2 on HarmonyOS PC.

   Exercises real public APIs of the installed libraries:
   - Qmmp::strVersion() / Qmmp::configDir() / Qmmp::pluginPath() (libqmmp)
   - Qmmp::findPlugins("<Category>/") decoder/plugin discovery over the
     installed plugin tree
   - Qmmp::CueParser over an in-memory CUE sheet (parses the file name,
     performers and offsets of the generated tracks)
*/
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QStringList>

#include <qmmp/cueparser.h>
#include <qmmp/qmmp.h>

#include <cstdio>

namespace
{
int failures = 0;

void check(bool condition, const char *what)
{
    if (condition) {
        std::printf("PASS %s\n", what);
    } else {
        std::printf("FAIL %s\n", what);
        ++failures;
    }
}
} // namespace

int main(int argc, char **argv)
{
    // QApplication is not required, but the installed libraries link against
    // Qt Widgets; QCoreApplication keeps the test headless.
    QCoreApplication app(argc, argv);

    // --- libqmmp: version and paths ---------------------------------------
    {
        const QString version = Qmmp::strVersion();
        std::printf("     Qmmp::strVersion() = %s\n", qPrintable(version));
        check(version == QStringLiteral("2.3.2"), "Qmmp::strVersion()");

        check(!Qmmp::configDir().isEmpty(), "Qmmp::configDir() is set");
        check(!Qmmp::pluginPath().isEmpty(), "Qmmp::pluginPath() is set");
    }

    // --- libqmmp: plugin discovery over the installed plugin tree ---------
    {
        QStringList expected = {
            QStringLiteral("flac"),
            QStringLiteral("vorbis"),
            QStringLiteral("opus"),
            QStringLiteral("mpeg"),
            QStringLiteral("sndfile"),
            QStringLiteral("wavpack"),
            QStringLiteral("wildmidi"),
            QStringLiteral("archive"),
            QStringLiteral("cue"),
        };
        const QStringList decoders = Qmmp::findPlugins(QStringLiteral("Input/"));
        // qmmp installs its plugins as lib<name>.so, the loader returns the
        // canonical file paths.
        std::printf("     Input plugins found: %d\n", int(decoders.size()));
        for (const QString &name : expected) {
            bool found = false;
            for (const QString &plugin : decoders) {
                QString base = QFileInfo(plugin).completeBaseName();
                if (base.startsWith(QLatin1String("lib"))) {
                    base.remove(0, 3);
                }
                if (base == name) {
                    found = true;
                    break;
                }
            }
            check(found, qPrintable(QStringLiteral("decoder plugin '%1' installed").arg(name)));
        }

        const QStringList outputs = Qmmp::findPlugins(QStringLiteral("Output/"));
        std::printf("     Output plugins found: %d\n", int(outputs.size()));
        check(!outputs.isEmpty(), "output plugins installed");

        const QStringList effects = Qmmp::findPlugins(QStringLiteral("Effect/"));
        std::printf("     Effect plugins found: %d\n", int(effects.size()));
        check(!effects.isEmpty(), "effect plugins installed");
    }

    // --- libqmmp: CUE sheet parsing ---------------------------------------
    {
        const QByteArray cue =
            "REM GENRE Test\n"
            "PERFORMER \"Consumer Test\"\n"
            "TITLE \"qmmp consumer test\"\n"
            "FILE \"consumer.flac\" WAVE\n"
            "  TRACK 01 AUDIO\n"
            "    TITLE \"first\"\n"
            "    PERFORMER \"Artist One\"\n"
            "    INDEX 01 00:00:00\n"
            "  TRACK 02 AUDIO\n"
            "    TITLE \"second\"\n"
            "    PERFORMER \"Artist Two\"\n"
            "    INDEX 01 03:30:00\n";
        CueParser parser;
        parser.loadData(cue, "UTF-8");
        const QStringList files = parser.files();
        std::printf("     CUE files parsed: %d\n", int(files.size()));
        check(files.size() == 1 && files.first().endsWith(QStringLiteral("consumer.flac")),
              "CueParser::files()");
        check(parser.offset(2) == 210000, "CueParser::offset(2) == 210000 ms");
        const QList<TrackInfo *> tracks = parser.createPlayList();
        check(tracks.size() == 2, "CueParser::createPlayList() returns 2 tracks");
        for (TrackInfo *track : tracks) {
            delete track;
        }
    }

    if (failures == 0) {
        std::printf("ALL PASS\n");
        return 0;
    }
    std::printf("%d FAILURE(S)\n", failures);
    return 1;
}
