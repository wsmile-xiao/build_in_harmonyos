#include <QCoreApplication>
#include <QLocale>
#include <QStringList>
#include <QTextToSpeech>

#include <cmath>
#include <iostream>

namespace {
int fail(const char *message)
{
    std::cerr << message << '\n';
    return 1;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const QStringList engines = QTextToSpeech::availableEngines();
    if (!engines.contains(QStringLiteral("mock")))
        return fail("The installed mock text-to-speech engine was not discovered");

    QTextToSpeech speech(QStringLiteral("mock"));
    if (speech.state() != QTextToSpeech::Ready)
        return fail("The mock text-to-speech engine is not ready");
    if (speech.engine() != QStringLiteral("mock"))
        return fail("QTextToSpeech did not select the requested mock engine");
    if (speech.availableLocales().isEmpty())
        return fail("The mock engine did not expose any locale");
    if (speech.availableVoices().isEmpty())
        return fail("The mock engine did not expose any voice");

    speech.setRate(0.25);
    speech.setPitch(-0.5);
    speech.setVolume(0.75);
    if (std::abs(speech.rate() - 0.25) > 0.001)
        return fail("Rate property round-trip failed");
    if (std::abs(speech.pitch() + 0.5) > 0.001)
        return fail("Pitch property round-trip failed");
    if (std::abs(speech.volume() - 0.75) > 0.001)
        return fail("Volume property round-trip failed");

    std::cout << "qtspeech consumer test passed with mock engine\n";
    return 0;
}
