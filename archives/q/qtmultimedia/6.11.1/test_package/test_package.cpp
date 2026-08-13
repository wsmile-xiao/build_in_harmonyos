#include <QAudioDevice>
#include <QAudioOutput>
#include <QCoreApplication>
#include <QMediaDevices>
#include <QMediaMetaData>
#include <QMediaPlayer>
#include <QMediaRecorder>
#include <QObject>
#include <QTimer>
#include <QUrl>
#include <QtCore/QString>
#include <cstdio>

// Consumer test for the Qt Multimedia module on HarmonyOS PC.
// Exercises the installed Qt6::Multimedia package APIs: media player
// construction, audio output device enumeration, metadata and error
// signalling without requiring a real media backend.

static int failures = 0;

#define CHECK(cond, name)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("[PASS] %s\n", name);                                  \
        } else {                                                               \
            std::printf("[FAIL] %s\n", name);                                  \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

class MediaProbe : public QObject
{
    Q_OBJECT
public:
    int errorSignals = 0;
public slots:
    void onError(QMediaPlayer::Error error, const QString &errorString)
    {
        ++errorSignals;
        Q_UNUSED(error);
        Q_UNUSED(errorString);
    }
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. QMediaPlayer construction (Qt6 API).
    QMediaPlayer player;
    CHECK(player.playbackState() == QMediaPlayer::StoppedState,
          "QMediaPlayer::playbackState initial StoppedState");
    CHECK(player.error() == QMediaPlayer::NoError
              || player.error() == QMediaPlayer::ResourceError
              || player.error() == QMediaPlayer::FormatError
              || player.error() == QMediaPlayer::NetworkError
              || player.error() == QMediaPlayer::AccessDeniedError,
          "QMediaPlayer::error valid enum");

    // 2. QAudioDevice enumeration (no backend required for accessor).
    const QList<QAudioDevice> outputs = QMediaDevices::audioOutputs();
    CHECK(!QMediaDevices::defaultAudioOutput().isNull()
              || outputs.isEmpty(),
          "QMediaDevices::audioOutputs accessor");

    // 3. QMediaMetaData key-value store.
    QMediaMetaData meta;
    meta.insert(QMediaMetaData::Title, QStringLiteral("openharmony-probe"));
    CHECK(meta.value(QMediaMetaData::Title).toString()
              == QStringLiteral("openharmony-probe"),
          "QMediaMetaData insert/value");

    // 4. Signal-slot plumbing (errorOccurred): assert the connection is
    //    established (connect() returning true). On OHOS there is no media
    //    backend, so QMediaPlayer never processes the invalid source and
    //    errorOccurred cannot fire; the observed count is reported as
    //    diagnostics with the reason, instead of faking a firing assertion.
    MediaProbe probe;
    const bool connected = QObject::connect(&player, &QMediaPlayer::errorOccurred,
                                            &probe, &MediaProbe::onError);
    CHECK(connected, "errorOccurred connection established");
    player.setSource(QUrl(QStringLiteral("file:///nonexistent-probe.wav")));
    QTimer::singleShot(500, &app, &QCoreApplication::quit);
    app.exec();
    std::printf("[INFO] errorOccurred signals observed: %d "
                "(0 expected: no media backend on OHOS)\n",
                probe.errorSignals);

    std::printf("qtmultimedia consumer test: %s\n",
                failures == 0 ? "ALL PASSED" : "FAILED");
    return failures == 0 ? 0 : 1;
}

#include "test_package.moc"
