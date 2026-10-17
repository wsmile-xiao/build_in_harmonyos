#ifndef QT6_HARMONYOS_QT_LOCAL_SOCKET_TEST_H
#define QT6_HARMONYOS_QT_LOCAL_SOCKET_TEST_H

#include <string>

namespace qt6_harmonyos {

std::string startQtLocalEchoServer();
std::string qtLocalEchoServerStatus();
std::string stopQtLocalEchoServer();
std::string probeQtLocalSocket(const std::string &fullServerName,
                               const std::string &payload,
                               int timeoutMilliseconds);

} // namespace qt6_harmonyos

#endif
