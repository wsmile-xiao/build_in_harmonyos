// Consumer test: Arcus::Socket lifecycle without network I/O.
// Matches upstream src/Socket.cpp: close() in Initial state reports
// InvalidStateError and stays Initial (it never transitions to Closed),
// and reset() requires Closed/Error. Each numbered check prints on
// failure; exit 0 means all 6 checks passed.
#include <Arcus/Socket.h>
#include <Arcus/SocketListener.h>
#include <Arcus/Types.h>

#include <cstdio>

namespace
{
class DummyListener : public Arcus::SocketListener
{
public:
    void stateChanged(Arcus::SocketState) override {}
    void messageReceived() override {}
    void error(const Arcus::Error&) override {}
};
} // namespace

int main()
{
    Arcus::Socket socket;

    // 1. Fresh socket starts in Initial state.
    if (socket.getState() != Arcus::SocketState::Initial)
    {
        std::printf("FAIL 1: fresh socket state is not Initial\n");
        return 1;
    }

    // 2. No error is set on a fresh socket.
    if (socket.getLastError().isValid())
    {
        std::printf("FAIL 2: fresh socket reports a valid error\n");
        return 2;
    }

    // 3. close() in Initial is invalid: stays Initial + InvalidStateError.
    socket.close();
    if (socket.getState() != Arcus::SocketState::Initial)
    {
        std::printf("FAIL 3: close() in Initial state left Initial\n");
        return 3;
    }
    if (!socket.getLastError().isValid() ||
        socket.getLastError().getErrorCode() != Arcus::ErrorCode::InvalidStateError)
    {
        std::printf("FAIL 3: close() in Initial state must set InvalidStateError\n");
        return 3;
    }

    // 4. clearError clears the close() error, state stays Initial.
    socket.clearError();
    if (socket.getLastError().isValid())
    {
        std::printf("FAIL 4: error still valid after clearError\n");
        return 4;
    }
    if (socket.getState() != Arcus::SocketState::Initial)
    {
        std::printf("FAIL 4: state left Initial after clearError\n");
        return 4;
    }

    // 5. Listener add/remove works in Initial state without error.
    DummyListener listener;
    socket.addListener(&listener);
    socket.removeListener(&listener);
    if (socket.getState() != Arcus::SocketState::Initial ||
        socket.getLastError().isValid())
    {
        std::printf("FAIL 5: add/removeListener disturbed Initial state\n");
        return 5;
    }

    // 6. reset() in Initial is invalid: stays Initial + InvalidStateError.
    socket.reset();
    if (socket.getState() != Arcus::SocketState::Initial)
    {
        std::printf("FAIL 6: reset() in Initial state left Initial\n");
        return 6;
    }
    if (!socket.getLastError().isValid() ||
        socket.getLastError().getErrorCode() != Arcus::ErrorCode::InvalidStateError)
    {
        std::printf("FAIL 6: reset() in Initial state must set InvalidStateError\n");
        return 6;
    }
    socket.clearError();

    std::printf("test_socket OK: 6 socket lifecycle checks passed\n");
    return 0;
}
