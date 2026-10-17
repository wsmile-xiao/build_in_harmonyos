#include <QCoreApplication>
#include <QtTextToSpeech/QTextToSpeech>

#include <cstdlib>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    const QStringList engines = QTextToSpeech::availableEngines();
    QTextToSpeech speech(engines.isEmpty() ? QString() : engines.first());

    if (!engines.isEmpty() && speech.engine() != engines.first())
        return EXIT_FAILURE;

    if (speech.state() == QTextToSpeech::Error && speech.errorReason() == QTextToSpeech::ErrorReason::NoError)
        return EXIT_FAILURE;

    const auto capabilities = speech.engineCapabilities();
    if (!engines.isEmpty() && capabilities == QTextToSpeech::Capability::None && speech.state() != QTextToSpeech::Error)
        return EXIT_FAILURE;

    return EXIT_SUCCESS;
}
