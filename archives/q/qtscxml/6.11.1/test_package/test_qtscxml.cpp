// Consumer test for Qt6Scxml / Qt6StateMachine on HarmonyOS PC.
// Verifies the packaged Qt6::Scxml and Qt6::StateMachine APIs are usable:
//  - QScxmlStateMachine parses and starts an inline SCXML document.
//  - QStateMachine runs a simple two-state machine.

#include <QBuffer>
#include <QCoreApplication>
#include <QScxmlStateMachine>
#include <QState>
#include <QStateMachine>
#include <cstdio>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // ── Qt6::StateMachine ──
    {
        QStateMachine machine;
        QState *s1 = new QState(&machine);
        QState *s2 = new QState(&machine);
        machine.setInitialState(s1);
        machine.start();
        app.processEvents();
        if (!machine.isRunning()) {
            std::fprintf(stderr,
                         "test_qtscxml: QStateMachine failed to start\n");
            return 1;
        }
        machine.stop();
    }

    // ── Qt6::Scxml ──
    {
        const QByteArray scxmlData =
            "<scxml xmlns=\"http://www.w3.org/2005/07/scxml\" "
            "version=\"1.0\" initial=\"idle\">"
            "<state id=\"idle\"><transition event=\"go\" target=\"done\"/>"
            "</state><final id=\"done\"/></scxml>";
        QBuffer buffer;
        buffer.setData(scxmlData);
        if (!buffer.open(QIODevice::ReadOnly)) {
            std::fprintf(stderr,
                         "test_qtscxml: failed to open SCXML buffer\n");
            return 1;
        }
        QScxmlStateMachine *machine = QScxmlStateMachine::fromData(&buffer);
        if (!machine) {
            std::fprintf(
                stderr,
                "test_qtscxml: QScxmlStateMachine::fromData returned null\n");
            return 1;
        }
        if (!machine->parseErrors().isEmpty()) {
            std::fprintf(stderr,
                         "test_qtscxml: SCXML parse errors reported\n");
            delete machine;
            return 1;
        }
        machine->start();
        app.processEvents();
        if (!machine->isRunning()) {
            std::fprintf(
                stderr,
                "test_qtscxml: QScxmlStateMachine failed to start\n");
            delete machine;
            return 1;
        }
        delete machine;
    }

    std::printf(
        "test_qtscxml: Qt6::Scxml and Qt6::StateMachine smoke test OK\n");
    return 0;
}
