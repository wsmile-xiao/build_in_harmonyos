#include <QCoreApplication>
#include <QTextToSpeech>
#include <QStringList>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    QStringList engines = QTextToSpeech::availableEngines();
    QTextToSpeech speech(engines.isEmpty() ? QString() : engines.first());
    QTextToSpeech::State state = speech.state();
    (void)state;
    std::printf("Available engines: %d\n", engines.size());
    std::printf("QtSpeech test PASSED\n");
    return 0;
}
