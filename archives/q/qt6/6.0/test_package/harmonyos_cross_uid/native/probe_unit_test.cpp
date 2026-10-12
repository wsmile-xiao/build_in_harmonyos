#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "socket_probe.h"

#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <atomic>
#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>

namespace {

bool writeAll(int descriptor, const std::string &bytes)
{
    size_t offset = 0;
    while (offset < bytes.size()) {
        const ssize_t written = ::send(descriptor, bytes.data() + offset,
                                       bytes.size() - offset, 0);
        if (written <= 0)
            return false;
        offset += static_cast<size_t>(written);
    }
    return true;
}

int createAbstractListener(const std::string &fullServerName)
{
    if (fullServerName.empty() || fullServerName.front() != '@')
        return -1;

    sockaddr_un address{};
    const std::string key = fullServerName.substr(1);
    if (key.empty() || key.size() + 1 > sizeof(address.sun_path))
        return -1;

    const int descriptor = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (descriptor < 0)
        return -1;

    address.sun_family = AF_UNIX;
    std::memcpy(address.sun_path + 1, key.data(), key.size());
    const socklen_t addressLength = static_cast<socklen_t>(
        offsetof(sockaddr_un, sun_path) + 1 + key.size());
    if (::bind(descriptor, reinterpret_cast<const sockaddr *>(&address),
               addressLength) != 0
        || ::listen(descriptor, 1) != 0) {
        ::close(descriptor);
        return -1;
    }
    return descriptor;
}

bool check(bool condition, const char *description)
{
    if (!condition)
        std::fprintf(stderr, "FAIL: %s\n", description);
    return condition;
}

} // namespace

int main(int argc, char **argv)
{
    if (argc == 3 && std::strcmp(argv[1], "--connect") == 0) {
        const std::string payload = "QT6-HARMONYOS-REVERSE-UID-PROBE";
        const qt6_harmonyos::SocketProbeResult result =
            qt6_harmonyos::probeAbstractSocket(argv[2], payload, 3000);
        std::printf("connected=%s\nlocal_uid=%lu\npeer_credentials_read=%s\n"
                    "peer_uid=%lu\npeer_pid=%ld\npayload_sent=%s\n"
                    "sent_bytes=%zu\nresponse_received=%s\nresponse_bytes=%zu\n"
                    "error_number=%d\ndetail=%s\n",
                    result.connected ? "true" : "false",
                    static_cast<unsigned long>(result.localUid),
                    result.peerCredentialsRead ? "true" : "false",
                    static_cast<unsigned long>(result.peerUid),
                    static_cast<long>(result.peerPid),
                    result.payloadSent ? "true" : "false",
                    result.payloadSent ? payload.size() : 0,
                    result.responseReceived ? "true" : "false",
                    result.response.size(), result.errorNumber,
                    result.detail.c_str());
        return result.connected && result.peerCredentialsRead
                && result.payloadSent
            ? 0 : 1;
    }
    if (argc != 1) {
        std::fprintf(stderr, "usage: %s [--connect @qt6:<uid>:<64-hex>]\n",
                     argv[0]);
        return 2;
    }

    const uid_t currentUid = ::geteuid();
    const std::string serverName = "@qt6:" + std::to_string(currentUid)
        + ":" + std::string(64, 'a');
    const std::string payload = "HarmonyOS AF_UNIX probe echo payload";
    const int listener = createAbstractListener(serverName);
    if (!check(listener >= 0, "bind the HarmonyOS abstract AF_UNIX listener"))
        return 1;

    std::atomic<bool> serverExchangePassed{false};
    std::thread server([&] {
        const int accepted = ::accept(listener, nullptr, nullptr);
        if (accepted < 0)
            return;

        ucred peer{};
        socklen_t peerLength = sizeof(peer);
        const bool credentialsRead = ::getsockopt(accepted, SOL_SOCKET,
                                                   SO_PEERCRED, &peer,
                                                   &peerLength) == 0
            && peerLength == sizeof(peer) && peer.uid == currentUid;

        std::string received;
        char buffer[64];
        ssize_t count = 0;
        while ((count = ::recv(accepted, buffer, sizeof(buffer), 0)) > 0)
            received.append(buffer, static_cast<size_t>(count));

        const std::string response = "echo:" + received;
        const bool echoed = credentialsRead && received == payload
            && writeAll(accepted, response);
        serverExchangePassed.store(echoed);
        ::shutdown(accepted, SHUT_WR);
        ::close(accepted);
    });

    const qt6_harmonyos::SocketProbeResult result =
        qt6_harmonyos::probeAbstractSocket(serverName, payload, 3000);
    ::close(listener);
    server.join();

    const qt6_harmonyos::SocketProbeResult malformed =
        qt6_harmonyos::probeAbstractSocket("not-an-abstract-qt-name", payload,
                                           100);
    const qt6_harmonyos::SocketProbeResult invalidHash =
        qt6_harmonyos::probeAbstractSocket(
            "@qt6:" + std::to_string(currentUid) + ":not-a-sha256", payload,
            100);
    const std::string tooLongName = "@qt6:" + std::to_string(currentUid)
        + ":" + std::string(256, 'x');
    const qt6_harmonyos::SocketProbeResult tooLong =
        qt6_harmonyos::probeAbstractSocket(tooLongName, payload, 100);

    qt6_harmonyos::AbstractEchoServer managedServer;
    std::string managedServerName;
    std::string managedServerError;
    const bool managedServerStarted = managedServer.start(
        &managedServerName, &managedServerError);
    const qt6_harmonyos::SocketProbeResult managedServerResult = managedServerStarted
        ? qt6_harmonyos::probeAbstractSocket(managedServerName, payload, 3000)
        : qt6_harmonyos::SocketProbeResult{};
    const bool managedServerFinished = managedServerStarted
        && managedServer.waitForConnection(3000);
    const uid_t managedServerPeerUid = managedServer.peerUid();
    const std::string managedServerPayload = managedServer.receivedPayload();
    const bool managedServerEchoed = managedServer.responseSent();
    managedServer.stop();

    const bool passed = check(result.connected, "connect to abstract AF_UNIX")
        && check(result.peerCredentialsRead, "read SO_PEERCRED from the peer")
        && check(result.localUid == currentUid, "report the local effective UID")
        && check(result.peerUid == currentUid, "report the same-UID echo peer")
        && check(result.payloadSent, "send a real payload to the echo server")
        && check(result.responseReceived && result.response == "echo:" + payload,
                 "receive the exact server echo")
        && check(serverExchangePassed.load(), "server validates credentials and payload")
        && check(!malformed.connected && malformed.errorNumber == EINVAL,
                 "reject an address without the reserved @qt6: prefix")
        && check(!invalidHash.connected && invalidHash.errorNumber == EINVAL,
                 "reject a non-SHA256 @qt6: endpoint")
        && check(!tooLong.connected && tooLong.errorNumber == ENAMETOOLONG,
                 "reject an abstract name larger than sun_path")
        && check(managedServerStarted,
                 managedServerError.empty()
                     ? "start an independent abstract echo server"
                     : managedServerError.c_str())
        && check(managedServerResult.connected,
                 "connect to the independent abstract echo server")
        && check(managedServerResult.peerCredentialsRead
                     && managedServerResult.peerUid == managedServer.localUid(),
                 "read the independent server's same-UID peer credentials")
        && check(managedServerResult.responseReceived
                     && managedServerResult.response == "echo:" + payload,
                 "receive the independent server's exact echo")
        && check(managedServerFinished && managedServerPeerUid == currentUid,
                 "independent server observes the client's effective UID")
        && check(managedServerPayload == payload && managedServerEchoed,
                 "independent server receives and echoes real payload bytes");

    if (!passed)
        return 1;

    std::printf("TEST_RESULT=PASS\nlocal_uid=%lu peer_uid=%lu peer_pid=%ld\n"
                "sent_bytes=%zu response_bytes=%zu response=%s\n",
                static_cast<unsigned long>(result.localUid),
                static_cast<unsigned long>(result.peerUid),
                static_cast<long>(result.peerPid), payload.size(),
                result.response.size(), result.response.c_str());
    return 0;
}
