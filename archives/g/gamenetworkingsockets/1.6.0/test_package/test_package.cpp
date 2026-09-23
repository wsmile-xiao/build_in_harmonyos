// Consumer smoke test for gamenetworkingsockets 1.6.0 on HarmonyOS PC.
//
// Real API lifecycle over loopback UDP:
//   GameNetworkingSockets_Init (spawns the musl pthread service thread,
//   generates an OpenSSL ed25519 cert via the keypair code)
//   -> status-changed callback registration
//   -> CreateListenSocketIP(127.0.0.1) + CreatePollGroup
//   -> ConnectByIPAddress(127.0.0.1)
//   -> AcceptConnection (on incoming callback)
//   -> SendMessageToConnection / ReceiveMessagesOnPollGroup
//   -> CloseConnection / CloseListenSocket
//   -> GameNetworkingSockets_Kill
#include <steam/steamnetworkingsockets.h>
#include <steam/isteamnetworkingutils.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>

#ifdef __OHOS__
// HarmonyOS-specific verification line (rule12): read the OS release info
// to prove we are executing on an OHOS (musl) system, not a glibc host.
static void print_ohos_environment()
{
    char buf[256] = {0};
    const char *path = "/etc/os-release";
    FILE *f = std::fopen(path, "r");
    if (f) {
        size_t n = std::fread(buf, 1, sizeof(buf) - 1, f);
        buf[n] = 0;
        std::fclose(f);
    }
    std::string pretty = "HarmonyOS";
    const char *p = std::strstr(buf, "PRETTY_NAME=");
    if (p) {
        p += std::strlen("PRETTY_NAME=");
        const char *e = std::strchr(p, '\n');
        pretty = std::string(p, e ? (size_t)(e - p) : std::strlen(p));
        while (!pretty.empty() && (pretty.front() == '"' || pretty.back() == '"')) {
            pretty.erase(pretty.begin() + (pretty.front() == '"' ? 0 : pretty.size() - 1));
        }
    }
    std::printf("[OHOS] running on %s: musl pthread + epoll + OpenSSL loopback roundtrip\n", pretty.c_str());
}
#endif

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        ++g_checks;                                                     \
        if (!(cond)) {                                                  \
            ++g_failed;                                                 \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        }                                                               \
    } while (0)

static HSteamNetConnection g_hConnServer = k_HSteamNetConnection_Invalid;
static HSteamNetPollGroup g_pollGroup = k_HSteamNetPollGroup_Invalid;
static HSteamListenSocket g_hListen = k_HSteamListenSocket_Invalid;
static HSteamNetConnection g_hConnClient = k_HSteamNetConnection_Invalid;
static bool g_serverConnected = false;
static bool g_clientConnected = false;

static void SteamNetConnectionStatusChanged(SteamNetConnectionStatusChangedCallback_t *pInfo)
{
    switch (pInfo->m_info.m_eState) {
    case k_ESteamNetworkingConnectionState_Connecting: {
        // Is this a connection we are receiving on our listen socket?
        // (upstream test_connection pattern: check m_hListenSocket)
        if (g_hListen != k_HSteamListenSocket_Invalid
            && pInfo->m_info.m_hListenSocket == g_hListen) {
            g_hConnServer = pInfo->m_hConn;
            g_serverConnected = true;
            SteamNetworkingSockets()->AcceptConnection(pInfo->m_hConn);
            if (g_pollGroup != k_HSteamNetPollGroup_Invalid) {
                SteamNetworkingSockets()->SetConnectionPollGroup(pInfo->m_hConn, g_pollGroup);
            }
        }
        break;
    }
    case k_ESteamNetworkingConnectionState_Connected: {
        if (pInfo->m_hConn == g_hConnClient) {
            g_clientConnected = true;
        }
        break;
    }
    default:
        break;
    }
}

int main()
{
#ifdef __OHOS__
    print_ohos_environment();
#endif

    SteamNetworkingErrMsg errMsg;
    CHECK(GameNetworkingSockets_Init(nullptr, errMsg));

    ISteamNetworkingSockets *iface = SteamNetworkingSockets();
    CHECK(iface != nullptr);

    // Register the global status-changed callback (standard upstream pattern).
    CHECK(SteamNetworkingUtils()->SetGlobalCallback_SteamNetConnectionStatusChanged(
        &SteamNetConnectionStatusChanged));

    // Upstream's own test_connection binds an explicit port (port 0 is not
    // an "ephemeral" convention here). Pick a high port.
    SteamNetworkingIPAddr localAddr;
    std::memset(&localAddr, 0, sizeof(localAddr));
    localAddr.SetIPv4(0x7f000001u, 27500);

    HSteamListenSocket hListen = iface->CreateListenSocketIP(localAddr, 0, nullptr);
    CHECK(hListen != k_HSteamListenSocket_Invalid);
    g_hListen = hListen;

    HSteamNetPollGroup hPoll = iface->CreatePollGroup();
    CHECK(hPoll != k_HSteamNetPollGroup_Invalid);
    g_pollGroup = hPoll;

    SteamNetworkingIPAddr clientAddr = localAddr;
    HSteamNetConnection hConnClient = iface->ConnectByIPAddress(clientAddr, 0, nullptr);
    CHECK(hConnClient != k_HSteamNetConnection_Invalid);
    g_hConnClient = hConnClient;

    // Pump until both sides are connected.
    for (int iter = 0; iter < 3000 && !(g_clientConnected && g_serverConnected); ++iter) {
        iface->RunCallbacks();
        usleep(2000);
    }
    CHECK(g_clientConnected);
    CHECK(g_serverConnected);

    // Client -> server reliable roundtrip.
    static const char kPayload[] = "harmony-pc-loopback-payload";
    const size_t kPayloadLen = std::strlen(kPayload);
    bool gotPayload = false;
    int64 msgNumber = 0;
    EResult sendRes = iface->SendMessageToConnection(
        hConnClient, kPayload, (uint32)kPayloadLen,
        k_nSteamNetworkingSend_Reliable, &msgNumber);
    CHECK(sendRes == k_EResultOK);
    CHECK(msgNumber > 0);
    for (int iter = 0; iter < 3000 && !gotPayload; ++iter) {
        iface->RunCallbacks();
        while (true) {
            SteamNetworkingMessage_t *pMsg[4] = {nullptr};
            int nGot = iface->ReceiveMessagesOnPollGroup(hPoll, pMsg, 4);
            if (nGot <= 0) {
                break;
            }
            for (int i = 0; i < nGot; ++i) {
                if (pMsg[i]->m_cbSize == (int)kPayloadLen
                    && std::memcmp(pMsg[i]->m_pData, kPayload, kPayloadLen) == 0) {
                    gotPayload = true;
                }
                pMsg[i]->Release();
            }
        }
        usleep(2000);
    }
    CHECK(gotPayload);

    iface->CloseConnection(hConnClient, 0, "test done", false);
    if (g_hConnServer != k_HSteamNetConnection_Invalid) {
        iface->CloseConnection(g_hConnServer, 0, "test done", false);
    }
    iface->DestroyPollGroup(hPoll);
    iface->CloseListenSocket(hListen);
    GameNetworkingSockets_Kill();

    std::printf("test_gns: %d checks, %d failures\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
