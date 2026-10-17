#include <QCoreApplication>
#include <QMediaPlayer>
#include <QAudioDeviceInfo>
#include <QList>
#include <QUrl>

// Qt5 Multimedia smoke test: build QMediaPlayer, query available audio
// output devices (QAudioDeviceInfo::availableDevices) and set media. On OHOS
// there is no real multimedia backend, so we only verify construction + API
// surface, not playback.
int main(int argc, char *argv[]) {
    QCoreApplication application(argc, argv);

    // QMediaPlayer construction exercises the QtMultimedia private libs.
    QMediaPlayer *player = new QMediaPlayer();
    if (player == nullptr)
        return 1;

    // QAudioDeviceInfo::availableDevices() returns a list; on OHOS this may
    // be empty (no audio backend), which is acceptable — the call itself
    // proves the Qt5::Multimedia binary links and runs.
    QList<QAudioDeviceInfo> devices = QAudioDeviceInfo::availableDevices(
        QAudio::AudioOutput);
    (void)devices;

    // Set a dummy media source and confirm the player accepted it. In Qt 5.15
    // QMediaContent is a plain wrapper (no isValid()), so just exercise the
    // setMedia/state API surface.
    player->setMedia(QUrl("qrc:///dummy.mp4"));
    if (player->media().isNull())
        return 2;
    if (player->state() != QMediaPlayer::StoppedState)
        return 3;

    delete player;
    return 0;
}
