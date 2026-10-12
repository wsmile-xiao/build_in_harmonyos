#ifndef QT6_HARMONYOS_SOCKET_PROBE_H
#define QT6_HARMONYOS_SOCKET_PROBE_H

#include <sys/types.h>

#include <memory>
#include <string>

namespace qt6_harmonyos {

struct SocketProbeResult
{
    bool connected = false;
    bool peerCredentialsRead = false;
    bool payloadSent = false;
    bool responseReceived = false;
    uid_t localUid = static_cast<uid_t>(-1);
    uid_t expectedServerUid = static_cast<uid_t>(-1);
    uid_t peerUid = static_cast<uid_t>(-1);
    pid_t peerPid = -1;
    int errorNumber = 0;
    std::string response;
    std::string detail;
};

SocketProbeResult probeAbstractSocket(const std::string &fullServerName,
                                     const std::string &payload,
                                     int timeoutMilliseconds);

class AbstractEchoServer
{
public:
    AbstractEchoServer();
    ~AbstractEchoServer();

    AbstractEchoServer(const AbstractEchoServer &) = delete;
    AbstractEchoServer &operator=(const AbstractEchoServer &) = delete;

    bool start(std::string *fullServerName, std::string *error);
    bool waitForConnection(int timeoutMilliseconds);
    void stop();
    uid_t localUid() const;
    uid_t peerUid() const;
    std::string receivedPayload() const;
    bool responseSent() const;
    bool active() const;
    bool finished() const;
    bool accepted() const;
    bool peerCredentialsRead() const;
    pid_t peerPid() const;
    std::string error() const;

private:
    struct Impl;
    std::unique_ptr<Impl> d;
};

} // namespace qt6_harmonyos

#endif
