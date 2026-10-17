// Consumer smoke test for yojimbo 1.13.5 on HarmonyOS PC.
//
// Mirrors upstream test.cpp's test_client_server_messages (loopback path):
//   Server::Start on 127.0.0.1 -> Client::InsecureConnect (netcode connect
//   token handshake + libsodium AEAD encryption over UDP loopback)
//   -> bidirectional reliable-ordered message exchange (plain + block
//   messages) -> clean disconnect -> Server::Stop.
// Exercises the vendored netcode/reliable/sodium/tlsf objects folded into
// the installed archive end to end, on the musl/OHOS POSIX path.
#include <yojimbo.h>

#include <cstdio>
#include <cstring>
#include <unistd.h>
#include <sys/utsname.h>

// HarmonyOS environment verification line (rule12): probe the running OS
// with uname() — pure POSIX (sys/utsname.h), no platform branch, compiles
// and runs unconditionally on every platform (R8: no platform-conditional
// macros in source). On OHOS the kernel reports sysname "HarmonyOS" and
// machine "aarch64", which is the actual runtime evidence for the
// verification line — not a hard-coded fallback string.
static void print_ohos_environment()
{
    struct utsname u;
    if (uname(&u) != 0) {
        std::printf("[OHOS] uname() failed: environment verification line unavailable\n");
        return;
    }
    std::printf("[OHOS] running on %s (kernel: %s, machine: %s): "
                "musl BSD-sockets + libsodium AEAD loopback session\n",
                u.sysname, u.release, u.machine);
}

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

using namespace yojimbo;

static const uint64_t ProtocolId = 0x11223344556677ULL;
static const int ClientPort = 30100;
static const int ServerPort = 40100;
static const int MaxTestClients = 4;
static const int ReliableChannel = 0;

static int GetNumBitsForMessage(uint16_t sequence)
{
    static int messageBitsArray[] = { 1, 320, 120, 4, 256, 45, 11, 13, 101, 100, 84, 95, 203, 2, 3, 8, 512, 5, 3, 7, 50 };
    const int modulus = sizeof(messageBitsArray) / sizeof(int);
    const int index = sequence % modulus;
    return messageBitsArray[index];
}

struct TestMessage : public Message
{
    uint16_t sequence;

    TestMessage() : sequence(0) {}

    template <typename Stream> bool Serialize(Stream & stream)
    {
        serialize_bits(stream, sequence, 16);

        int numBits = GetNumBitsForMessage(sequence);
        int numWords = numBits / 32;
        uint32_t dummy = 0;
        for (int i = 0; i < numWords; ++i)
            serialize_bits(stream, dummy, 32);
        int numRemainderBits = numBits - numWords * 32;
        if (numRemainderBits > 0)
            serialize_bits(stream, dummy, numRemainderBits);

        return true;
    }

    YOJIMBO_VIRTUAL_SERIALIZE_FUNCTIONS()
};

struct TestBlockMessage : public BlockMessage
{
    uint16_t sequence;

    TestBlockMessage() : sequence(0) {}

    template <typename Stream> bool Serialize(Stream & stream)
    {
        serialize_bits(stream, sequence, 16);
        return true;
    }

    YOJIMBO_VIRTUAL_SERIALIZE_FUNCTIONS()
};

enum TestMessageType
{
    TEST_MESSAGE,
    TEST_BLOCK_MESSAGE,
    NUM_TEST_MESSAGE_TYPES
};

YOJIMBO_MESSAGE_FACTORY_START(TestMessageFactory, NUM_TEST_MESSAGE_TYPES);
YOJIMBO_DECLARE_MESSAGE_TYPE(TEST_MESSAGE, TestMessage);
YOJIMBO_DECLARE_MESSAGE_TYPE(TEST_BLOCK_MESSAGE, TestBlockMessage);
YOJIMBO_MESSAGE_FACTORY_FINISH();

class TestAdapter : public Adapter
{
public:
    MessageFactory * CreateMessageFactory(Allocator & allocator)
    {
        return YOJIMBO_NEW(allocator, TestMessageFactory, allocator);
    }
};

static TestAdapter adapter;

static void PumpClientServerUpdate(double & time, Client & client, Server & server, float deltaTime = 0.1f)
{
    client.SendPackets();
    server.SendPackets();
    client.ReceivePackets();
    server.ReceivePackets();
    time += deltaTime;
    client.AdvanceTime(time);
    server.AdvanceTime(time);
    yojimbo_sleep(0.0f);
}

int main()
{
    // Unconditional (R8): POSIX-only environment probe, runs on every
    // platform so the rule12 verification line can never silently vanish.
    print_ohos_environment();

    CHECK(InitializeYojimbo());

    const uint64_t clientId = 1;

    Address clientAddress("0.0.0.0", ClientPort);
    Address serverAddress("127.0.0.1", ServerPort);

    double time = 100.0;

    ClientServerConfig config;
    config.channel[ReliableChannel].messageSendQueueSize = 16;
    config.channel[ReliableChannel].maxMessagesPerPacket = 8;
    config.channel[ReliableChannel].maxBlockSize = 1024;
    config.channel[ReliableChannel].blockFragmentSize = 200;
    config.protocolId = ProtocolId;
    config.timeout = 10;

    uint8_t privateKey[KeyBytes];
    std::memset(privateKey, 0, KeyBytes);

    Client client(GetDefaultAllocator(), clientAddress, config, adapter, time);
    Server server(GetDefaultAllocator(), privateKey, serverAddress, config, adapter, time);

    CHECK(server.Start(MaxTestClients));

    // Insecure connect: skips the matchmaker, mints the connect token
    // locally, still runs the full netcode handshake + libsodium AEAD.
    client.InsecureConnect(privateKey, clientId, serverAddress);

    const int NumHandshakeIters = 10000;
    bool connected = false;
    for (int i = 0; i < NumHandshakeIters; ++i)
    {
        PumpClientServerUpdate(time, client, server);
        if (client.ConnectionFailed())
            break;
        if (!client.IsConnecting() && client.IsConnected() && server.GetNumConnectedClients() == 1) {
            connected = true;
            break;
        }
    }

    CHECK(connected);
    CHECK(client.IsConnected());
    CHECK(server.GetNumConnectedClients() == 1);
    CHECK(client.GetClientIndex() == 0);
    CHECK(server.IsClientConnected(0));

    // Bidirectional message exchange over the encrypted loopback channel.
    const int NumMessagesSent = 16;

    for (int i = 0; i < NumMessagesSent; ++i)
    {
        CHECK(client.CanSendMessage(ReliableChannel));
        if (i % 3) {
            TestMessage * message = (TestMessage *) client.CreateMessage(TEST_MESSAGE);
            CHECK(message);
            message->sequence = (uint16_t) i;
            client.SendMessage(ReliableChannel, message);
        } else {
            TestBlockMessage * message = (TestBlockMessage *) client.CreateMessage(TEST_BLOCK_MESSAGE);
            CHECK(message);
            message->sequence = (uint16_t) i;
            const int blockSize = 1 + ((i * 901) % 1001);
            uint8_t * blockData = client.AllocateBlock(blockSize);
            CHECK(blockData);
            for (int j = 0; j < blockSize; ++j)
                blockData[j] = (uint8_t)(i + j);
            client.AttachBlockToMessage(message, blockData, blockSize);
            client.SendMessage(ReliableChannel, message);
        }

        CHECK(server.CanSendMessage(0, ReliableChannel));
        TestMessage * reply = (TestMessage *) server.CreateMessage(0, TEST_MESSAGE);
        CHECK(reply);
        reply->sequence = (uint16_t) i;
        server.SendMessage(0, ReliableChannel, reply);
    }

    int numReceivedFromClient = 0;
    int numReceivedFromServer = 0;

    const int NumDrainIters = 10000;
    for (int i = 0; i < NumDrainIters; ++i)
    {
        PumpClientServerUpdate(time, client, server);

        if (!client.IsConnected())
            break;

        while (true)
        {
            Message * message = client.ReceiveMessage(ReliableChannel);
            if (!message)
                break;
            CHECK(message->GetId() == numReceivedFromServer);
            CHECK(message->GetType() == TEST_MESSAGE);
            TestMessage * testMessage = (TestMessage *) message;
            CHECK(testMessage->sequence == (uint16_t) numReceivedFromServer);
            ++numReceivedFromServer;
            client.ReleaseMessage(message);
        }

        while (true)
        {
            Message * message = server.ReceiveMessage(0, ReliableChannel);
            if (!message)
                break;
            CHECK(message->GetId() == numReceivedFromClient);
            if (message->GetType() == TEST_MESSAGE) {
                TestMessage * testMessage = (TestMessage *) message;
                CHECK(testMessage->sequence == (uint16_t) numReceivedFromClient);
                ++numReceivedFromClient;
            } else {
                CHECK(message->IsBlockMessage());
                TestBlockMessage * blockMessage = (TestBlockMessage *) message;
                CHECK(blockMessage->sequence == (uint16_t) numReceivedFromClient);
                const int blockSize = blockMessage->GetBlockSize();
                CHECK(blockSize == 1 + ((numReceivedFromClient * 901) % 1001));
                const uint8_t * blockData = blockMessage->GetBlockData();
                CHECK(blockData);
                for (int j = 0; j < blockSize; ++j) {
                    CHECK(blockData[j] == (uint8_t)(numReceivedFromClient + j));
                }
                ++numReceivedFromClient;
            }
            server.ReleaseMessage(0, message);
        }

        if (numReceivedFromClient == NumMessagesSent && numReceivedFromServer == NumMessagesSent)
            break;
    }

    CHECK(numReceivedFromClient == NumMessagesSent);
    CHECK(numReceivedFromServer == NumMessagesSent);

    // Clean disconnect, both sides drain to zero.
    client.Disconnect();
    for (int i = 0; i < NumHandshakeIters; ++i)
    {
        PumpClientServerUpdate(time, client, server);
        if (!client.IsConnected() && server.GetNumConnectedClients() == 0)
            break;
    }
    CHECK(!client.IsConnected());
    CHECK(server.GetNumConnectedClients() == 0);

    server.Stop();

    ShutdownYojimbo();

    std::printf("%s: %d checks, %d failed\n", g_failed ? "FAILED" : "PASSED", g_checks, g_failed);
    return g_failed ? 1 : 0;
}
