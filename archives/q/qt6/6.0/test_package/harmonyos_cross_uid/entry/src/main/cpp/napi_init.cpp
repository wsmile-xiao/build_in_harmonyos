#include "napi/native_api.h"

#include "socket_probe.h"
#include "qt_local_socket_test.h"

#include <cerrno>
#include <sstream>
#include <string>
#include <vector>

namespace {

bool readString(napi_env env, napi_value value, std::string *result)
{
    size_t length = 0;
    if (napi_get_value_string_utf8(env, value, nullptr, 0, &length) != napi_ok)
        return false;

    std::vector<char> buffer(length + 1);
    if (napi_get_value_string_utf8(env, value, buffer.data(), buffer.size(),
                                   &length) != napi_ok)
        return false;
    result->assign(buffer.data(), length);
    return true;
}

qt6_harmonyos::AbstractEchoServer &diagnosticServer()
{
    static qt6_harmonyos::AbstractEchoServer server;
    return server;
}

napi_value toJsString(napi_env env, const std::string &value)
{
    napi_value output = nullptr;
    napi_create_string_utf8(env, value.c_str(), value.size(), &output);
    return output;
}

napi_value Probe(napi_env env, napi_callback_info info)
{
    size_t argumentCount = 2;
    napi_value arguments[2] = {nullptr, nullptr};
    if (napi_get_cb_info(env, info, &argumentCount, arguments, nullptr, nullptr)
            != napi_ok
        || argumentCount != 2) {
        napi_throw_type_error(env, nullptr, "probe expects server name and payload");
        return nullptr;
    }

    std::string serverName;
    std::string payload;
    if (!readString(env, arguments[0], &serverName)
        || !readString(env, arguments[1], &payload)) {
        napi_throw_type_error(env, nullptr, "server name and payload must be strings");
        return nullptr;
    }

    const qt6_harmonyos::SocketProbeResult result =
        qt6_harmonyos::probeAbstractSocket(serverName, payload, 3000);
    std::ostringstream report;
    report << "connected=" << (result.connected ? "true" : "false") << '\n'
           << "local_uid=" << static_cast<unsigned long>(result.localUid) << '\n'
           << "expected_server_uid="
           << static_cast<unsigned long>(result.expectedServerUid) << '\n'
           << "peer_credentials_read="
           << (result.peerCredentialsRead ? "true" : "false") << '\n'
           << "peer_uid=" << static_cast<unsigned long>(result.peerUid) << '\n'
           << "peer_pid=" << static_cast<long>(result.peerPid) << '\n'
           << "different_uid="
           << (result.peerCredentialsRead && result.localUid != result.peerUid
                   ? "true" : "false") << '\n'
           << "payload_sent=" << (result.payloadSent ? "true" : "false") << '\n'
           << "sent_bytes=" << (result.payloadSent ? payload.size() : 0) << '\n'
           << "response_received="
           << (result.responseReceived ? "true" : "false") << '\n'
           << "response_bytes=" << result.response.size() << '\n'
           << "error_number=" << result.errorNumber << '\n'
           << "detail=" << result.detail;

    return toJsString(env, report.str());
}

napi_value StartServer(napi_env env, napi_callback_info)
{
    std::string fullServerName;
    std::string error;
    const bool started = diagnosticServer().start(&fullServerName, &error);
    std::ostringstream report;
    report << "server_started=" << (started ? "true" : "false") << '\n'
           << "local_uid=" << static_cast<unsigned long>(diagnosticServer().localUid()) << '\n';
    if (started)
        report << "server_full_name=" << fullServerName;
    else
        report << "error=" << error;
    return toJsString(env, report.str());
}

napi_value ServerStatus(napi_env env, napi_callback_info)
{
    qt6_harmonyos::AbstractEchoServer &server = diagnosticServer();
    std::ostringstream report;
    report << "server_active=" << (server.active() ? "true" : "false") << '\n'
           << "server_finished=" << (server.finished() ? "true" : "false") << '\n'
           << "server_accepted=" << (server.accepted() ? "true" : "false") << '\n'
           << "local_uid=" << static_cast<unsigned long>(server.localUid()) << '\n'
           << "peer_credentials_read="
           << (server.peerCredentialsRead() ? "true" : "false") << '\n'
           << "peer_uid=" << static_cast<unsigned long>(server.peerUid()) << '\n'
           << "peer_pid=" << static_cast<long>(server.peerPid()) << '\n'
           << "payload_bytes=" << server.receivedPayload().size() << '\n'
           << "response_sent=" << (server.responseSent() ? "true" : "false") << '\n'
           << "error=" << server.error();
    return toJsString(env, report.str());
}

napi_value StopServer(napi_env env, napi_callback_info)
{
    diagnosticServer().stop();
    return toJsString(env, "server_stopped=true");
}

napi_value StartQtServer(napi_env env, napi_callback_info)
{
#if defined(QT6_HAP_WITH_QT)
    return toJsString(env, qt6_harmonyos::startQtLocalEchoServer());
#else
    return toJsString(env, "server_started=false\nerror=Qt runtime not staged");
#endif
}

napi_value QtServerStatus(napi_env env, napi_callback_info)
{
#if defined(QT6_HAP_WITH_QT)
    return toJsString(env, qt6_harmonyos::qtLocalEchoServerStatus());
#else
    return toJsString(env, "server_active=false\nerror=Qt runtime not staged");
#endif
}

napi_value StopQtServer(napi_env env, napi_callback_info)
{
#if defined(QT6_HAP_WITH_QT)
    return toJsString(env, qt6_harmonyos::stopQtLocalEchoServer());
#else
    return toJsString(env, "server_stopped=true");
#endif
}

napi_value QtProbe(napi_env env, napi_callback_info info)
{
#if defined(QT6_HAP_WITH_QT)
    size_t argumentCount = 2;
    napi_value arguments[2] = {nullptr, nullptr};
    if (napi_get_cb_info(env, info, &argumentCount, arguments, nullptr, nullptr)
                != napi_ok
            || argumentCount != 2) {
        napi_throw_type_error(env, nullptr, "qtProbe expects server name and payload");
        return nullptr;
    }

    std::string serverName;
    std::string payload;
    if (!readString(env, arguments[0], &serverName)
            || !readString(env, arguments[1], &payload)) {
        napi_throw_type_error(env, nullptr, "server name and payload must be strings");
        return nullptr;
    }
    return toJsString(env, qt6_harmonyos::probeQtLocalSocket(
            serverName, payload, 3000));
#else
    (void)info;
    return toJsString(env, "connected=false\nerror=Qt runtime not staged");
#endif
}

} // namespace

EXTERN_C_START
static napi_value Init(napi_env env, napi_value exports)
{
    napi_property_descriptor properties[] = {
        {"probe", nullptr, Probe, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"startServer", nullptr, StartServer, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"serverStatus", nullptr, ServerStatus, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"stopServer", nullptr, StopServer, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"startQtServer", nullptr, StartQtServer, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"qtServerStatus", nullptr, QtServerStatus, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"stopQtServer", nullptr, StopQtServer, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"qtProbe", nullptr, QtProbe, nullptr, nullptr, nullptr, napi_default, nullptr}
    };
    napi_define_properties(env, exports,
                           sizeof(properties) / sizeof(properties[0]), properties);
    return exports;
}
EXTERN_C_END

static napi_module module = {
    .nm_version = 1,
    .nm_flags = 0,
    .nm_filename = nullptr,
    .nm_register_func = Init,
    .nm_modname = "qt6uidprobe",
    .nm_priv = nullptr,
    .reserved = {0},
};

extern "C" __attribute__((constructor)) void RegisterQt6UidProbeModule(void)
{
    napi_module_register(&module);
}
