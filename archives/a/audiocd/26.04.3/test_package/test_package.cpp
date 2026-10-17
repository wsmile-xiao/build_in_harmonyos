/* Smoke test for audiocd (audiocdplugins) on HarmonyOS PC.
 *
 * The upstream audiocd tarball registers no test suite of its own
 * (no tests/, autotests/ or add_test() anywhere), so this consumer test
 * verifies the delivered audiocdplugins library surface directly, through
 * the public installed headers only (audiocdencoder.h + audiocdcdio.h):
 *
 *  - AudioCDEncoder / AudioCDDataSink base interfaces (the OHOS adaptation
 *    keeps the upstream data() call semantics via the sink abstraction)
 *  - create_audiocd_encoders symbol resolution on the installed encoder
 *    plugin libraries via QLibrary — the exact discovery mechanism of
 *    AudioCDEncoder::findAllPlugins
 *  - the wav plugin's EncoderWav/EncoderCda instances: RIFF/WAVE header
 *    emission through the sink (readInit), raw frame pass-through read()
 *    == CD_FRAMESIZE_RAW, size()/type()/mimeType()/fileType() and the
 *    KCDDB::CDInfo fillSongInfo plumbing (proves the libkcddb link)
 *  - the CD-DA frame constants from the self-contained audiocdcdio.h
 *    (the trimmed cdparanoia dependency)
 */
#include <QCoreApplication>
#include <QByteArray>
#include <QDebug>
#include <QLibrary>
#include <QString>
#include <QStringList>

#include <kcddb/CDInfo>

#include "audiocdencoder.h"
#include "audiocdcdio.h"

#include <cstdio>
#include <cstring>

// The data sink collecting the encoder output (equivalent of the KIO
// worker's data() stream on a KIO-enabled platform).
class CollectingSink : public AudioCDDataSink
{
public:
    void data(const QByteArray &d) override
    {
        m_chunks++;
        m_buffer.append(d);
    }
    int chunks() const { return m_chunks; }
    const QByteArray &buffer() const { return m_buffer; }

private:
    int m_chunks = 0;
    QByteArray m_buffer;
};

static int failures = 0;

#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            std::printf("FAIL: %s\n", msg); \
            failures++; \
        } else { \
            std::printf("PASS: %s\n", msg); \
        } \
    } while (0)

// Resolves create_audiocd_encoders on a plugin library and instantiates its
// encoders (the same symbol findAllPlugins resolves at runtime).
static QList<AudioCDEncoder *> loadPluginEncoders(const QString &libPath, bool *ok)
{
    *ok = false;
    QLibrary lib(libPath);
    if (!lib.load()) {
        std::printf("FAIL: cannot load %s: %s\n",
                    qPrintable(libPath), qPrintable(lib.errorString()));
        failures++;
        return {};
    }
    auto sym = reinterpret_cast<void (*)(AudioCDDataSink *, QList<AudioCDEncoder *> &)>(
        lib.resolve("create_audiocd_encoders"));
    if (!sym) {
        std::printf("FAIL: create_audiocd_encoders not found in %s\n", qPrintable(libPath));
        failures++;
        lib.unload();
        return {};
    }
    *ok = true;
    CollectingSink sink;
    QList<AudioCDEncoder *> encoders;
    sym(&sink, encoders);
    return encoders;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    Q_UNUSED(app);

    // ---- constants from the self-contained audiocdcdio.h ----
    CHECK(CD_FRAMESIZE_RAW == 2352, "CD_FRAMESIZE_RAW constant = 2352 (Red Book)");
    CHECK(CD_FRAMESAMPLES == 588, "CD_FRAMESAMPLES constant = 588");

    const QString pluginDir = QString::fromUtf8(::getenv("AUDIOCD_PLUGIN_DIR"));
    if (pluginDir.isEmpty()) {
        std::printf("SKIP: AUDIOCD_PLUGIN_DIR not set, plugin checks not exercised\n");
        std::printf(failures == 0 ? "ALL PASS\n" : "%d FAILURES\n", failures);
        return failures == 0 ? 0 : 1;
    }

    // ---- wav plugin: EncoderWav + EncoderCda ----
    {
        bool ok = false;
        QList<AudioCDEncoder *> encoders =
            loadPluginEncoders(pluginDir + QLatin1String("/libaudiocd_encoder_wav.so"), &ok);
        if (!ok) {
            // failure already counted
        } else {
            CHECK(encoders.size() == 2, "wav plugin creates 2 encoders (Wav + Cda)");

            AudioCDEncoder *wav = nullptr;
            AudioCDEncoder *cda = nullptr;
            for (AudioCDEncoder *e : encoders) {
                if (e->type() == QLatin1String("Wav"))
                    wav = e;
                else if (e->type() == QLatin1String("CDA"))
                    cda = e;
            }
            CHECK(wav != nullptr, "Wav encoder present");
            CHECK(cda != nullptr, "CDA encoder present");

            if (wav) {
                CHECK(wav->init(), "EncoderWav::init() returns true");
                CHECK(QString::fromLatin1(wav->mimeType()) == QLatin1String("audio/x-wav"),
                      "EncoderWav::mimeType() is audio/x-wav");
                CHECK(QString::fromLatin1(wav->fileType()) == QLatin1String("wav"),
                      "EncoderWav::fileType() is wav");
                // EncoderWav::size = EncoderCda::size + 44 byte header
                CHECK(wav->size(2) == 2 * 176400 + 44, "EncoderWav::size(2s) = 2*176400 + 44 header bytes");

                // KCDDB CDInfo handoff (proves the libkcddb link)
                KCDDB::CDInfo info;
                wav->fillSongInfo(info, 1, QString());

                CollectingSink sink;
                wav->ioSink = &sink;
                const long headerSize = wav->readInit(2 * 176400);
                CHECK(headerSize == 44, "readInit() emits the 44 byte RIFF header");
                CHECK(sink.chunks() == 1, "sink received exactly one chunk from readInit");
                CHECK(sink.buffer().size() == 44, "sink buffer holds 44 header bytes");
                CHECK(sink.buffer().startsWith("RIFF") && sink.buffer().mid(8, 4) == "WAVE",
                      "RIFF/WAVE magic present in the emitted header");
                // WAV header size fields are little-endian u32
                const QByteArray &hdr = sink.buffer();
                quint32 le32 = 0;
                auto readLE32 = [&hdr](int off) -> quint32 {
                    return (static_cast<unsigned char>(hdr[off]))
                         | (static_cast<unsigned char>(hdr[off + 1]) << 8)
                         | (static_cast<unsigned char>(hdr[off + 2]) << 16)
                         | (static_cast<unsigned char>(hdr[off + 3]) << 24);
                };
                le32 = readLE32(4);
                CHECK(le32 == 2 * 176400 + 44 - 8, "RIFF size field = byteCount + 44 - 8");
                le32 = readLE32(40);
                CHECK(le32 == 2 * 176400, "data size field = byteCount");
                CHECK(wav->readCleanup() == 0, "EncoderWav::readCleanup() = 0");
            }

            if (cda) {
                CHECK(cda->init(), "EncoderCda::init() returns true");
                CHECK(QString::fromLatin1(cda->mimeType()) == QLatin1String("audio/x-cda"),
                      "EncoderCda::mimeType() is audio/x-cda");
                CHECK(QString::fromLatin1(cda->fileType()) == QLatin1String("cda"),
                      "EncoderCda::fileType() is cda");
                CHECK(cda->size(1) == 176400, "EncoderCda::size(1s) = 176400");

                CollectingSink cdaSink;
                cda->ioSink = &cdaSink;
                qint16 samples[CD_FRAMESAMPLES];
                for (int i = 0; i < CD_FRAMESAMPLES; i++)
                    samples[i] = static_cast<qint16>(i);
                const long written = cda->read(samples, 1);
                CHECK(written == CD_FRAMESIZE_RAW, "EncoderCda::read() returns CD_FRAMESIZE_RAW");
                CHECK(cdaSink.buffer().size() == CD_FRAMESIZE_RAW,
                      "sink received CD_FRAMESIZE_RAW bytes from read()");
            }
            qDeleteAll(encoders);
        }
    }

    // ---- flac plugin loads and exposes its encoder ----
    {
        bool ok = false;
        QList<AudioCDEncoder *> encoders =
            loadPluginEncoders(pluginDir + QLatin1String("/libaudiocd_encoder_flac.so"), &ok);
        if (ok) {
            CHECK(encoders.size() == 1, "flac plugin creates 1 encoder");
            if (encoders.size() == 1) {
                AudioCDEncoder *flac = encoders.first();
                CHECK(flac->type() == QLatin1String("FLAC"), "flac encoder reports type FLAC");
                CHECK(QString::fromLatin1(flac->mimeType()) == QLatin1String("audio/x-flac"),
                      "flac encoder mimeType is audio/x-flac");
                // FLAC__stream_encoder_new() round trip (exercises the
                // conan flac link at runtime)
                CHECK(flac->init(), "EncoderFLAC::init() creates the stream encoder");
                CHECK(flac->readCleanup() == 0, "EncoderFLAC::readCleanup() returns 0");
                KCDDB::CDInfo info;
                flac->fillSongInfo(info, 1, QString());
            }
            qDeleteAll(encoders);
        }
    }

    // ---- vorbis plugin loads and exposes its encoder ----
    {
        bool ok = false;
        QList<AudioCDEncoder *> encoders =
            loadPluginEncoders(pluginDir + QLatin1String("/libaudiocd_encoder_vorbis.so"), &ok);
        if (ok) {
            CHECK(encoders.size() == 1, "vorbis plugin creates 1 encoder");
            if (encoders.size() == 1) {
                AudioCDEncoder *vorbis = encoders.first();
                CHECK(vorbis->type() == QLatin1String("Ogg Vorbis"),
                      "vorbis encoder reports type Ogg Vorbis");
                CHECK(QString::fromLatin1(vorbis->mimeType()) == QLatin1String("audio/x-vorbis+ogg"),
                      "vorbis encoder mimeType is audio/x-vorbis+ogg");
                // vorbis_info_init/vorbis_comment_init round trip (exercises
                // the conan libvorbis link at runtime)
                CHECK(vorbis->init(), "EncoderVorbis::init() inits the vorbis structs");
                KCDDB::CDInfo info;
                vorbis->fillSongInfo(info, 1, QString());
            }
            qDeleteAll(encoders);
        }
    }

    // ---- opus plugin loads and exposes its encoder ----
    {
        bool ok = false;
        QList<AudioCDEncoder *> encoders =
            loadPluginEncoders(pluginDir + QLatin1String("/libaudiocd_encoder_opus.so"), &ok);
        if (ok) {
            CHECK(encoders.size() == 1, "opus plugin creates 1 encoder");
            if (encoders.size() == 1) {
                AudioCDEncoder *opus = encoders.first();
                CHECK(opus->type() == QLatin1String("Opus"), "opus encoder reports type Opus");
                CHECK(QString::fromLatin1(opus->mimeType()) == QLatin1String("audio/x-opus+ogg"),
                      "opus encoder mimeType is audio/x-opus+ogg");
                // opus init() requires the external opusenc tool; only the
                // encoder object construction is asserted here (the plugin
                // wrapper defers to the external encoder at runtime)
                KCDDB::CDInfo info;
                opus->fillSongInfo(info, 1, QString());
            }
            qDeleteAll(encoders);
        }
    }

    std::printf(failures == 0 ? "ALL PASS\n" : "%d FAILURES\n", failures);
    return failures == 0 ? 0 : 1;
}
