#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "socket_probe.h"

#include <sys/socket.h>
#include <sys/un.h>

#include <poll.h>
#include <unistd.h>

#include <cerrno>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <condition_variable>
#include <iomanip>
#include <limits>
#include <mutex>
#include <random>
#include <sstream>
#include <thread>
#include <atomic>
#include <exception>

namespace qt6_harmonyos {
namespace {

bool parseAbstractServerName(const std::string &fullServerName,
                             uid_t *serverUid,
                             sockaddr_un *address,
                             socklen_t *addressLength)
{
    static const std::string prefix = "@qt6:";
    if (fullServerName.compare(0, prefix.size(), prefix) != 0) {
        errno = EINVAL;
        return false;
    }

    const size_t uidStart = prefix.size();
    const size_t uidEnd = fullServerName.find(':', uidStart);
    if (uidEnd == std::string::npos || uidEnd == uidStart
        || uidEnd + 1 >= fullServerName.size()) {
        errno = EINVAL;
        return false;
    }

    unsigned long parsedUid = 0;
    for (size_t index = uidStart; index < uidEnd; ++index) {
        const unsigned char digit = static_cast<unsigned char>(fullServerName[index]);
        if (digit < '0' || digit > '9') {
            errno = EINVAL;
            return false;
        }
        const unsigned long nextDigit = static_cast<unsigned long>(digit - '0');
        if (parsedUid > (std::numeric_limits<unsigned long>::max() - nextDigit) / 10) {
            errno = EINVAL;
            return false;
        }
        parsedUid = parsedUid * 10 + nextDigit;
    }
    if (parsedUid > static_cast<unsigned long>(std::numeric_limits<uid_t>::max())) {
        errno = EINVAL;
        return false;
    }

    const std::string key = fullServerName.substr(1);
    if (key.size() + 1 > sizeof(address->sun_path)) {
        errno = ENAMETOOLONG;
        return false;
    }

    const std::string digest = fullServerName.substr(uidEnd + 1);
    if (digest.size() != 64) {
        errno = EINVAL;
        return false;
    }
    for (const unsigned char digit : digest) {
        if (!((digit >= '0' && digit <= '9') || (digit >= 'a' && digit <= 'f'))) {
            errno = EINVAL;
            return false;
        }
    }

    std::memset(address, 0, sizeof(*address));
    address->sun_family = AF_UNIX;
    std::memcpy(address->sun_path + 1, key.data(), key.size());
    *addressLength = static_cast<socklen_t>(offsetof(sockaddr_un, sun_path)
                                            + 1 + key.size());
    *serverUid = static_cast<uid_t>(parsedUid);
    return true;
}

std::string describeError(const char *operation, int errorNumber)
{
    return std::string(operation) + ": " + std::strerror(errorNumber);
}

bool sendAll(int descriptor, const std::string &bytes)
{
    size_t sent = 0;
    while (sent < bytes.size()) {
#ifdef MSG_NOSIGNAL
        const ssize_t count = ::send(descriptor, bytes.data() + sent,
                                     bytes.size() - sent, MSG_NOSIGNAL);
#else
        const ssize_t count = ::send(descriptor, bytes.data() + sent,
                                     bytes.size() - sent, 0);
#endif
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0)
            return false;
        sent += static_cast<size_t>(count);
    }
    return true;
}

std::string makeDiagnosticServerName(uid_t uid)
{
    static std::atomic<uint64_t> sequence{0};
    const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
    std::seed_seq seed{
        static_cast<unsigned>(::getpid()),
        static_cast<unsigned>(now),
        static_cast<unsigned>(now >> 32),
        static_cast<unsigned>(sequence.fetch_add(1, std::memory_order_relaxed))
    };
    std::mt19937_64 random(seed);

    std::ostringstream name;
    name << "@qt6:" << static_cast<unsigned long>(uid) << ':'
         << std::hex << std::setfill('0');
    for (int i = 0; i < 4; ++i)
        name << std::setw(16) << random();
    return name.str();
}

} // namespace

SocketProbeResult probeAbstractSocket(const std::string &fullServerName,
                                     const std::string &payload,
                                     int timeoutMilliseconds)
{
    SocketProbeResult result;
    result.localUid = ::geteuid();

    sockaddr_un address{};
    uid_t expectedServerUid = static_cast<uid_t>(-1);
    socklen_t addressLength = 0;
    if (!parseAbstractServerName(fullServerName, &expectedServerUid, &address,
                                 &addressLength)) {
        result.errorNumber = errno;
        result.detail = describeError("invalid abstract server name", errno);
        return result;
    }
    result.expectedServerUid = expectedServerUid;

    const int descriptor = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (descriptor < 0) {
        result.errorNumber = errno;
        result.detail = describeError("socket", errno);
        return result;
    }

    if (::connect(descriptor, reinterpret_cast<const sockaddr *>(&address),
                  addressLength) != 0) {
        result.errorNumber = errno;
        result.detail = describeError("connect", errno);
        ::close(descriptor);
        return result;
    }
    result.connected = true;

    ucred peer{};
    socklen_t peerLength = sizeof(peer);
    if (::getsockopt(descriptor, SOL_SOCKET, SO_PEERCRED, &peer,
                     &peerLength) == 0 && peerLength == sizeof(peer)) {
        result.peerCredentialsRead = true;
        result.peerUid = peer.uid;
        result.peerPid = peer.pid;
        if (peer.uid != expectedServerUid) {
            result.errorNumber = EPROTO;
            result.detail = "SO_PEERCRED UID does not match the UID in fullServerName";
            ::close(descriptor);
            return result;
        }
    } else {
        result.errorNumber = errno ? errno : EPROTO;
        result.detail = describeError("getsockopt(SO_PEERCRED)", result.errorNumber);
        ::close(descriptor);
        return result;
    }

    size_t sent = 0;
    while (sent < payload.size()) {
#ifdef MSG_NOSIGNAL
        const ssize_t count = ::send(descriptor, payload.data() + sent,
                                     payload.size() - sent, MSG_NOSIGNAL);
#else
        const ssize_t count = ::send(descriptor, payload.data() + sent,
                                     payload.size() - sent, 0);
#endif
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0) {
            result.errorNumber = count == 0 ? EPIPE : errno;
            result.detail = describeError("send", result.errorNumber);
            ::close(descriptor);
            return result;
        }
        sent += static_cast<size_t>(count);
    }
    result.payloadSent = true;
    if (::shutdown(descriptor, SHUT_WR) != 0) {
        result.errorNumber = errno;
        result.detail = describeError("shutdown(SHUT_WR)", errno);
        ::close(descriptor);
        return result;
    }

    const auto deadline = std::chrono::steady_clock::now()
        + std::chrono::milliseconds(timeoutMilliseconds > 0
                                        ? timeoutMilliseconds : 1);
    char buffer[1024];
    for (;;) {
        const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
            deadline - std::chrono::steady_clock::now()).count();
        if (remaining <= 0) {
            result.detail = result.response.empty()
                ? "connected and sent payload; no Qt response before timeout"
                : "received a partial response before timeout";
            break;
        }

        pollfd event{};
        event.fd = descriptor;
        event.events = POLLIN;
        const int ready = ::poll(&event, 1, static_cast<int>(remaining));
        if (ready < 0 && errno == EINTR)
            continue;
        if (ready == 0) {
            result.detail = result.response.empty()
                ? "connected and sent payload; no Qt response before timeout"
                : "received a partial response before timeout";
            break;
        }
        if (ready < 0) {
            result.errorNumber = errno;
            result.detail = describeError("poll", errno);
            break;
        }

        const ssize_t count = ::recv(descriptor, buffer, sizeof(buffer), 0);
        if (count < 0 && errno == EINTR)
            continue;
        if (count < 0) {
            result.errorNumber = errno;
            result.detail = describeError("recv", errno);
            break;
        }
        if (count == 0) {
            result.responseReceived = !result.response.empty();
            result.detail = result.responseReceived
                ? "received response and peer closed"
                : "kernel connection succeeded; peer closed without a Qt response";
            break;
        }
        result.response.append(buffer, static_cast<size_t>(count));
    }

    ::close(descriptor);
    return result;
}

struct AbstractEchoServer::Impl
{
    mutable std::mutex mutex;
    std::condition_variable condition;
    std::thread worker;
    int listener = -1;
    uid_t local = static_cast<uid_t>(-1);
    uid_t peer = static_cast<uid_t>(-1);
    pid_t pid = -1;
    bool active = false;
    bool stopping = false;
    bool done = false;
    bool wasAccepted = false;
    bool credentialsRead = false;
    bool echoed = false;
    std::string name;
    std::string payload;
    std::string failure;
};

AbstractEchoServer::AbstractEchoServer() : d(std::make_unique<Impl>())
{
}

AbstractEchoServer::~AbstractEchoServer()
{
    stop();
}

bool AbstractEchoServer::start(std::string *fullServerName, std::string *error)
{
    if (!fullServerName || !error) {
        errno = EINVAL;
        return false;
    }

    std::lock_guard<std::mutex> guard(d->mutex);
    if (d->active) {
        *error = "diagnostic abstract server has already been started";
        return false;
    }

    d->local = ::geteuid();
    d->name = makeDiagnosticServerName(d->local);
    sockaddr_un address{};
    const std::string key = d->name.substr(1);
    if (key.size() + 1 > sizeof(address.sun_path)) {
        *error = "diagnostic abstract server name exceeds sun_path";
        return false;
    }
    address.sun_family = AF_UNIX;
    std::memcpy(address.sun_path + 1, key.data(), key.size());
    const socklen_t addressLength = static_cast<socklen_t>(
        offsetof(sockaddr_un, sun_path) + 1 + key.size());

    const int listener = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (listener < 0) {
        *error = describeError("socket", errno);
        return false;
    }
    if (::bind(listener, reinterpret_cast<const sockaddr *>(&address),
               addressLength) != 0) {
        const int errorNumber = errno;
        ::close(listener);
        *error = describeError("bind", errorNumber);
        return false;
    }
    if (::listen(listener, 1) != 0) {
        const int errorNumber = errno;
        ::close(listener);
        *error = describeError("listen", errorNumber);
        return false;
    }

    d->listener = listener;
    d->active = true;
    d->stopping = false;
    d->done = false;
    d->wasAccepted = false;
    d->credentialsRead = false;
    d->echoed = false;
    d->peer = static_cast<uid_t>(-1);
    d->pid = -1;
    d->payload.clear();
    d->failure.clear();
    *fullServerName = d->name;
    error->clear();

    try {
        d->worker = std::thread([state = d.get(), listener] {
            int accepted = -1;
            for (;;) {
                {
                    std::lock_guard<std::mutex> stateGuard(state->mutex);
                    if (state->stopping)
                        break;
                }

                pollfd event{};
                event.fd = listener;
                event.events = POLLIN;
                const int ready = ::poll(&event, 1, 100);
                if (ready < 0 && errno == EINTR)
                    continue;
                if (ready < 0) {
                    std::lock_guard<std::mutex> stateGuard(state->mutex);
                    state->failure = describeError("poll(listener)", errno);
                    break;
                }
                if (ready == 0)
                    continue;
                if (!(event.revents & POLLIN))
                    continue;
                accepted = ::accept(listener, nullptr, nullptr);
                if (accepted < 0 && errno == EINTR)
                    continue;
                break;
            }

            if (accepted >= 0) {
                ucred credentials{};
                socklen_t credentialsLength = sizeof(credentials);
                const bool credentialsRead = ::getsockopt(
                    accepted, SOL_SOCKET, SO_PEERCRED, &credentials,
                    &credentialsLength) == 0
                    && credentialsLength == sizeof(credentials);
                {
                    std::lock_guard<std::mutex> stateGuard(state->mutex);
                    state->wasAccepted = true;
                    state->credentialsRead = credentialsRead;
                    if (credentialsRead) {
                        state->peer = credentials.uid;
                        state->pid = credentials.pid;
                    }
                }

                std::string payload;
                char buffer[1024];
                const auto deadline = std::chrono::steady_clock::now()
                    + std::chrono::seconds(10);
                for (;;) {
                    const auto remaining = std::chrono::duration_cast<
                        std::chrono::milliseconds>(deadline
                                                   - std::chrono::steady_clock::now()).count();
                    if (remaining <= 0)
                        break;
                    pollfd input{};
                    input.fd = accepted;
                    input.events = POLLIN;
                    const int inputReady = ::poll(&input, 1,
                                                  static_cast<int>(remaining));
                    if (inputReady < 0 && errno == EINTR)
                        continue;
                    if (inputReady <= 0)
                        break;
                    const ssize_t count = ::recv(accepted, buffer, sizeof(buffer), 0);
                    if (count < 0 && errno == EINTR)
                        continue;
                    if (count <= 0)
                        break;
                    payload.append(buffer, static_cast<size_t>(count));
                }

                const bool echoed = sendAll(accepted, "echo:" + payload);
                ::shutdown(accepted, SHUT_WR);
                ::close(accepted);
                std::lock_guard<std::mutex> stateGuard(state->mutex);
                state->payload = std::move(payload);
                state->echoed = echoed;
            }

            ::close(listener);
            {
                std::lock_guard<std::mutex> stateGuard(state->mutex);
                state->listener = -1;
                state->done = true;
            }
            state->condition.notify_all();
        });
    } catch (const std::exception &exception) {
        const int errorNumber = errno;
        d->active = false;
        d->listener = -1;
        ::close(listener);
        *error = std::string("start server thread: ") + exception.what();
        if (errorNumber != 0)
            *error += " (" + std::string(std::strerror(errorNumber)) + ')';
        return false;
    }
    return true;
}

bool AbstractEchoServer::waitForConnection(int timeoutMilliseconds)
{
    std::unique_lock<std::mutex> guard(d->mutex);
    return d->condition.wait_for(guard,
                                 std::chrono::milliseconds(timeoutMilliseconds),
                                 [this] { return d->done; });
}

void AbstractEchoServer::stop()
{
    int listener = -1;
    {
        std::lock_guard<std::mutex> guard(d->mutex);
        if (!d->active)
            return;
        d->stopping = true;
        listener = d->listener;
    }
    if (listener >= 0)
        ::shutdown(listener, SHUT_RDWR);
    if (d->worker.joinable())
        d->worker.join();
    std::lock_guard<std::mutex> guard(d->mutex);
    d->active = false;
}

uid_t AbstractEchoServer::localUid() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->local;
}

uid_t AbstractEchoServer::peerUid() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->peer;
}

std::string AbstractEchoServer::receivedPayload() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->payload;
}

bool AbstractEchoServer::responseSent() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->echoed;
}

bool AbstractEchoServer::active() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->active;
}

bool AbstractEchoServer::finished() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->done;
}

bool AbstractEchoServer::accepted() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->wasAccepted;
}

bool AbstractEchoServer::peerCredentialsRead() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->credentialsRead;
}

pid_t AbstractEchoServer::peerPid() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->pid;
}

std::string AbstractEchoServer::error() const
{
    std::lock_guard<std::mutex> guard(d->mutex);
    return d->failure;
}

} // namespace qt6_harmonyos
