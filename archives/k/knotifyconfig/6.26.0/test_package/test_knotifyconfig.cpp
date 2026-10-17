// knotifyconfig 6.26.0 consumer test (R34: exercises the real public API).
//
// Drives KNotifyConfigWidget through a complete read -> modify -> save round
// trip against a notifyrc file this test seeds itself:
//
//   setApplication()   -> KNotifyEventList::fill() parses [Event/...] groups
//                         out of $XDG_CONFIG_HOME/<app>.notifyrc
//   selectEvent()      -> KNotifyConfigActionsWidget::setConfigElement(),
//                         which on OHOS goes through QLineEdit::setText()
//                         instead of the upstream KUrlRequester::setUrl()
//   disableAllSounds() -> strips "Sound" from the cached Action entry
//   save()             -> flushes the cache back to disk, taking the Sound
//                         value from QLineEdit::text()
//
// The last two assertions read the file back, so a build that lost either
// OHOS-patched line (setText at setConfigElement, text at save) fails here
// instead of silently shipping a widget that forgets the configured sound.
#include <KNotifyConfigWidget>

#include <QApplication>
#include <QByteArray>
#include <QDir>
#include <QFile>
#include <QObject>
#include <QLatin1Char>
#include <QLatin1String>
#include <QString>
#include <QStringList>

#include <cstdio>

namespace {

const char kApplicationName[] = "knotifyconfig-consumer";
const char kEventGroup[] = "[Event/test-event]";

int fail(const char *what)
{
    std::fprintf(stderr, "FAIL: %s\n", what);
    return 1;
}

// $XDG_CONFIG_HOME/<app>.notifyrc -- KConfig resolves a bare file name
// against QStandardPaths::GenericConfigLocation, which is XDG_CONFIG_HOME.
QString configFilePath()
{
    const QByteArray configHome = qgetenv("XDG_CONFIG_HOME");
    if (configHome.isEmpty()) {
        return QString();
    }
    return QDir(QString::fromLocal8Bit(configHome)).filePath(QStringLiteral("knotifyconfig-consumer.notifyrc"));
}

bool writeSeedFile(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text)) {
        return false;
    }
    file.write("[Event/test-event]\n"
               "Name=Round Trip\n"
               "Comment=Synthetic event seeded by the consumer test\n"
               "Action=Sound|Popup\n"
               "Sound=bell.ogg\n");
    file.close();
    return true;
}

// Flat INI reader: returns the value of \a key inside the
// [Event/test-event] group, or a null QString when absent.
QString readBack(const QString &path, const QString &key)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return QString();
    }
    const QStringList lines = QString::fromUtf8(file.readAll()).split(QLatin1Char('\n'));
    bool inGroup = false;
    QString found;
    for (const QString &raw : lines) {
        const QString line = raw.trimmed();
        if (line.startsWith(QLatin1Char('['))) {
            inGroup = (line == QLatin1String(kEventGroup));
            continue;
        }
        if (!inGroup || line.isEmpty() || line.startsWith(QLatin1Char('#'))) {
            continue;
        }
        const int eq = line.indexOf(QLatin1Char('='));
        if (eq > 0 && line.left(eq) == key) {
            found = line.mid(eq + 1);
        }
    }
    return found;
}

} // namespace

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    Q_UNUSED(app);

    const QString path = configFilePath();
    if (path.isEmpty()) {
        return fail("XDG_CONFIG_HOME is not set");
    }
    if (!writeSeedFile(path)) {
        std::fprintf(stderr, "FAIL: cannot seed %s\n", qPrintable(path));
        return 1;
    }

    // 1. The seed is well formed and the reader used by the assertions below
    //    sees exactly what we wrote.
    if (readBack(path, QStringLiteral("Action")) != QLatin1String("Sound|Popup")) {
        return fail("seed Action entry did not survive the seed write");
    }
    if (readBack(path, QStringLiteral("Sound")) != QLatin1String("bell.ogg")) {
        return fail("seed Sound entry did not survive the seed write");
    }

    KNotifyConfigWidget widget(nullptr);

    // 2. changed(bool) is the only observable the widget exposes, so use it
    //    to pin down which operations actually did work.
    int changes = 0;
    bool lastState = true;
    QObject::connect(&widget, &KNotifyConfigWidget::changed, [&changes, &lastState](bool state) {
        ++changes;
        lastState = state;
    });

    // 3. Load the event list from the seeded file, then hand the event to the
    //    actions widget (this is the setText() path on OHOS).
    widget.setApplication(QString::fromLatin1(kApplicationName));
    widget.selectEvent(QStringLiteral("test-event"));

    // 4. disableAllSounds() reports changed(true) only when the event list
    //    really contains an event carrying the "Sound" action.
    changes = 0;
    widget.disableAllSounds();
    if (changes != 1 || !lastState) {
        std::fprintf(stderr, "FAIL: disableAllSounds() emitted %d changed() signal(s), expected one changed(true)\n", changes);
        return 1;
    }

    // 5. save() flushes the cache and reports the widget is clean again.
    changes = 0;
    widget.save();
    if (changes != 1 || lastState) {
        std::fprintf(stderr, "FAIL: save() emitted %d changed() signal(s), expected one changed(false)\n", changes);
        return 1;
    }

    // 6. The Sound action is gone ...
    const QString action = readBack(path, QStringLiteral("Action"));
    if (action != QLatin1String("Popup")) {
        std::fprintf(stderr, "FAIL: Action is \"%s\", expected \"Popup\"\n", qPrintable(action));
        return 1;
    }

    // 7. ... the sound *value* survived the round trip through the QLineEdit
    //     (this is the text() path -- empty here means setText() never ran) ...
    const QString sound = readBack(path, QStringLiteral("Sound"));
    if (sound != QLatin1String("bell.ogg")) {
        std::fprintf(stderr, "FAIL: Sound is \"%s\", expected \"bell.ogg\"\n", qPrintable(sound));
        return 1;
    }

    // 8. ... and unrelated entries in the same group were preserved.
    const QString name = readBack(path, QStringLiteral("Name"));
    if (name != QLatin1String("Round Trip")) {
        std::fprintf(stderr, "FAIL: Name is \"%s\", expected \"Round Trip\"\n", qPrintable(name));
        return 1;
    }

    std::printf("PASS: KNotifyConfigWidget save round trip verified OK\n");
    return 0;
}
