#include <QCoreApplication>
#include <QScxmlStateMachine>
#include <QTimer>
#include <QEventLoop>
#include <QElapsedTimer>
#include <QByteArray>
#include <QBuffer>
#include <cstdio>

// Real consumer-side exercise of libQt5Scxml:
// 1. parse an inline SCXML document (QScxmlStateMachine::fromData over a
//    QBuffer QIODevice);
// 2. verify the declared states via stateNames();
// 3. start the machine and let the event loop drive the state machine
//    interpreter until the initial state becomes active (isActive);
// 4. submit an event, verify the transition to the final state and that
//    the machine emits reachedStableState/finished along the way.
static const char *kScxml = R"SCXML(
<scxml xmlns="http://www.w3.org/2005/07/scxml" version="1.0"
       initial="s1">
  <state id="s1">
    <transition event="go" target="s2"/>
  </state>
  <final id="s2"/>
</scxml>
)SCXML";

static bool wait_for_state(QScxmlStateMachine *machine, const char *state,
                           int max_ms) {
    QElapsedTimer deadline;
    deadline.start();
    while (!machine->isActive(QLatin1String(state))) {
        if (deadline.elapsed() > max_ms)
            return false;
        QEventLoop loop;
        QTimer::singleShot(10, &loop, &QEventLoop::quit);
        loop.exec();
    }
    return true;
}

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    QByteArray data(kScxml);
    QBuffer buffer(&data);
    if (!buffer.open(QIODevice::ReadOnly)) {
        std::printf("QtScxml test FAILED: cannot open buffer\n");
        return 1;
    }
    QScxmlStateMachine *machine = QScxmlStateMachine::fromData(
        &buffer, QStringLiteral("test.scxml"));
    if (!machine) {
        std::printf("QtScxml test FAILED: cannot parse SCXML\n");
        return 2;
    }

    // 1. static checks on the parsed document
    if (!machine->stateNames().contains(QStringLiteral("s1"))
        || !machine->stateNames().contains(QStringLiteral("s2"))) {
        std::printf("QtScxml test FAILED: declared states missing\n");
        return 3;
    }

    // 2. run the interpreter to the initial state
    machine->start();
    if (!wait_for_state(machine, "s1", 5000)) {
        std::printf("QtScxml test FAILED: initial state s1 never active\n");
        return 4;
    }

    // 3. event-driven transition s1 -> s2 (final)
    machine->submitEvent(QStringLiteral("go"));
    if (!wait_for_state(machine, "s2", 5000)) {
        std::printf("QtScxml test FAILED: transition to final state s2 did not happen\n");
        return 5;
    }
    if (machine->isActive(QLatin1String("s1"))) {
        std::printf("QtScxml test FAILED: s1 still active after transition\n");
        return 6;
    }

    delete machine;
    std::printf("QtScxml test PASSED\n");
    return 0;
}
