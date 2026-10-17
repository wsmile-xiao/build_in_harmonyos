#include "qt_local_socket_test.h"

#include <QtNetwork/QLocalServer>
#include <QtNetwork/QLocalSocket>
#include <QtCore/QThread>
#include <QtCore/QByteArray>
#include <QtCore/QString>

#include <sys/socket.h>
#include <unistd.h>

#include <condition_variable>
#include <mutex>
#include <sstream>

namespace qt6_harmonyos {
namespace {

class QtLocalEchoServer final : public QThread
{
public:
    ~QtLocalEchoServer() override { stop(); }

    std::string start()
    {
        std::unique_lock<std::mutex> lock(mutex_);
        if (isRunning())
            return "server_started=true\nserver_full_name=" + fullServerName_;

        ready_ = false;
        active_ = false;
        accepted_ = false;
        peerCredentialsRead_ = false;
        peerUid_ = static_cast<uid_t>(-1);
        peerPid_ = -1;
        payload_.clear();
        responseSent_ = false;
        error_.clear();
        fullServerName_.clear();

        QThread::start();
        if (!condition_.wait_for(lock, std::chrono::seconds(5), [this] { return ready_; }))
            return "server_started=false\nerror=Qt QLocalServer listen timed out";

        if (!active_)
            return "server_started=false\nerror=" + error_;
        return "server_started=true\nlocal_uid=" + std::to_string(::geteuid())
                + "\nserver_full_name=" + fullServerName_;
    }

    std::string status()
    {
        std::lock_guard<std::mutex> lock(mutex_);
        std::ostringstream report;
        report << "server_active=" << (active_ ? "true" : "false") << '\n'
               << "server_accepted=" << (accepted_ ? "true" : "false") << '\n'
               << "peer_credentials_read=" << (peerCredentialsRead_ ? "true" : "false") << '\n'
               << "peer_uid=" << static_cast<unsigned long>(peerUid_) << '\n'
               << "peer_pid=" << static_cast<long>(peerPid_) << '\n'
               << "payload_bytes=" << payload_.size() << '\n'
               << "response_sent=" << (responseSent_ ? "true" : "false") << '\n'
               << "error=" << error_;
        return report.str();
    }

    std::string stop()
    {
        if (isRunning()) {
            requestInterruption();
            wait(5000);
        }
        return "server_stopped=true";
    }

protected:
    void run() override
    {
        QLocalServer server;
        const auto processPendingConnections = [this, &server] {
            while (server.hasPendingConnections()) {
                QLocalSocket *peer = server.nextPendingConnection();
                if (!peer)
                    continue;

                {
                    std::lock_guard<std::mutex> lock(mutex_);
                    accepted_ = true;
                    struct ucred credentials {};
                    socklen_t length = sizeof(credentials);
                    peerCredentialsRead_ = ::getsockopt(
                            static_cast<int>(peer->socketDescriptor()), SOL_SOCKET,
                            SO_PEERCRED, &credentials, &length) == 0
                            && length == sizeof(credentials);
                    if (peerCredentialsRead_) {
                        peerUid_ = credentials.uid;
                        peerPid_ = credentials.pid;
                    }
                }

                if (peer->bytesAvailable() == 0)
                    peer->waitForReadyRead(3000);
                const QByteArray request = peer->readAll();
                {
                    std::lock_guard<std::mutex> lock(mutex_);
                    payload_.assign(request.constData(), static_cast<size_t>(request.size()));
                }

                const QByteArray response = QByteArray("echo:") + request;
                const qint64 written = peer->write(response);
                const bool sent = written == response.size()
                        && peer->waitForBytesWritten(3000);
                {
                    std::lock_guard<std::mutex> lock(mutex_);
                    responseSent_ = sent;
                    if (!sent)
                        error_ = peer->errorString().toStdString();
                }
                peer->disconnectFromServer();
                peer->deleteLater();
            }
        };

        const QString requestedName = QString::fromLatin1("qt6-hap-cross-uid-%1-%2")
                .arg(static_cast<qulonglong>(::geteuid()))
                .arg(static_cast<qulonglong>(::getpid()));
        const bool listening = server.listen(requestedName);
        {
            std::lock_guard<std::mutex> lock(mutex_);
            ready_ = true;
            active_ = listening;
            if (listening)
                fullServerName_ = server.fullServerName().toStdString();
            else
                error_ = server.errorString().toStdString();
        }
        condition_.notify_all();
        if (!listening)
            return;

        // HAP's native runtime does not guarantee a Qt event dispatcher for
        // this worker thread.  The blocking API also works without an event
        // loop and keeps QLocalServer's accept path inside Qt itself.
        while (!isInterruptionRequested()) {
            if (server.waitForNewConnection(250))
                processPendingConnections();
        }
        server.close();
        std::lock_guard<std::mutex> lock(mutex_);
        active_ = false;
    }

private:
    std::mutex mutex_;
    std::condition_variable condition_;
    bool ready_ = false;
    bool active_ = false;
    bool accepted_ = false;
    bool peerCredentialsRead_ = false;
    bool responseSent_ = false;
    uid_t peerUid_ = static_cast<uid_t>(-1);
    pid_t peerPid_ = -1;
    std::string fullServerName_;
    std::string payload_;
    std::string error_;
};

QtLocalEchoServer &qtLocalEchoServer()
{
    static QtLocalEchoServer server;
    return server;
}

} // namespace

std::string startQtLocalEchoServer()
{
    return qtLocalEchoServer().start();
}

std::string qtLocalEchoServerStatus()
{
    return qtLocalEchoServer().status();
}

std::string stopQtLocalEchoServer()
{
    return qtLocalEchoServer().stop();
}

std::string probeQtLocalSocket(const std::string &fullServerName,
                               const std::string &payload,
                               int timeoutMilliseconds)
{
    QLocalSocket socket;
    socket.connectToServer(QString::fromUtf8(fullServerName.data(),
                                             static_cast<int>(fullServerName.size())));
    const bool connected = socket.waitForConnected(timeoutMilliseconds);
    bool peerCredentialsRead = false;
    uid_t peerUid = static_cast<uid_t>(-1);
    pid_t peerPid = -1;
    bool payloadSent = false;
    bool responseReceived = false;
    QByteArray response;

    if (connected) {
        struct ucred credentials {};
        socklen_t length = sizeof(credentials);
        peerCredentialsRead = ::getsockopt(static_cast<int>(socket.socketDescriptor()),
                                           SOL_SOCKET, SO_PEERCRED,
                                           &credentials, &length) == 0
                && length == sizeof(credentials);
        if (peerCredentialsRead) {
            peerUid = credentials.uid;
            peerPid = credentials.pid;
        }
        const QByteArray request(payload.data(), static_cast<int>(payload.size()));
        const qint64 written = socket.write(request);
        payloadSent = written == request.size()
                && socket.waitForBytesWritten(timeoutMilliseconds);
        responseReceived = socket.waitForReadyRead(timeoutMilliseconds);
        if (responseReceived)
            response = socket.readAll();
    }

    std::ostringstream report;
    report << "connected=" << (connected ? "true" : "false") << '\n'
           << "local_uid=" << static_cast<unsigned long>(::geteuid()) << '\n'
           << "peer_credentials_read=" << (peerCredentialsRead ? "true" : "false") << '\n'
           << "peer_uid=" << static_cast<unsigned long>(peerUid) << '\n'
           << "peer_pid=" << static_cast<long>(peerPid) << '\n'
           << "different_uid=" << (peerCredentialsRead && ::geteuid() != peerUid ? "true" : "false") << '\n'
           << "payload_sent=" << (payloadSent ? "true" : "false") << '\n'
           << "sent_bytes=" << (payloadSent ? payload.size() : 0) << '\n'
           << "response_received=" << (responseReceived ? "true" : "false") << '\n'
           << "response_bytes=" << response.size() << '\n'
           << "response=" << response.constData() << '\n'
           << "socket_error=" << socket.errorString().toStdString();
    return report.str();
}

} // namespace qt6_harmonyos
