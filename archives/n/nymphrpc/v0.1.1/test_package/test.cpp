// nymphrpc v0.1.1 test_package - verify library links and core API works
//
// This test verifies that:
// 1. The nymphrpc library can be linked (static)
// 2. Core types (NymphType) can be created and used
// 3. The NymphRemoteServer can be initialized
// 4. Message creation and serialization works

#include <nymph.h>

#include <cstdio>
#include <string>
#include <vector>

static int g_fail = 0;

#define CHECK(cond, what) \
    do { \
        if (!(cond)) { std::printf("FAIL %s\n", (what)); ++g_fail; } \
        else { std::printf("ok   %s\n", (what)); } \
    } while (0)

// Simple logger callback for NymphRemoteServer::init
// Upstream logFnc signature: void (*)(int level, std::string message)
void test_logger(int level, std::string msg) {
    // no-op logger for testing
    (void)level;
    (void)msg;
}

int main() {
    // Test 1: Initialize NymphRemoteServer
    bool init_ok = NymphRemoteServer::init(test_logger);
    CHECK(init_ok, "NymphRemoteServer::init");

    // Test 2: Create NymphType objects (core data type)
    NymphType uint32_val(static_cast<uint32_t>(42));
    uint32_t out_val = uint32_val.getUint32();
    CHECK(out_val == 42, "NymphType uint32 create+get");

    NymphType str_val(new std::string("hello nymphrpc"));
    std::string out_str = str_val.getString();
    CHECK(out_str == "hello nymphrpc", "NymphType string create+get");

    // Test 3: Create a NymphMessage
    NymphMessage msg(1);
    CHECK(msg.getMethodId() == 1, "NymphMessage methodId");

    // Test 4: Add a value to the message
    bool add_ok = msg.addValue(new NymphType(static_cast<uint32_t>(99)));
    CHECK(add_ok, "NymphMessage addValue");

    // Test 5: Get reply message
    NymphMessage* reply = msg.getReplyMessage();
    CHECK(reply != nullptr, "NymphMessage getReplyMessage");
    if (reply) {
        reply->setResultValue(new NymphType(static_cast<uint32_t>(1)));
        CHECK(reply->isReply(), "Reply message isReply flag");
        delete reply;
    }

    // Test 6: Double type
    NymphType dbl_val(3.14159);
    double out_dbl = dbl_val.getDouble();
    CHECK(out_dbl > 3.14 && out_dbl < 3.15, "NymphType double create+get");

    // Test 7: Boolean type
    NymphType bool_val(true);
    bool out_bool = bool_val.getBool();
    CHECK(out_bool == true, "NymphType bool create+get");

    // Test 8: Array type (vector of NymphType*)
    std::vector<NymphType*>* arr = new std::vector<NymphType*>();
    arr->push_back(new NymphType(static_cast<uint32_t>(1)));
    arr->push_back(new NymphType(static_cast<uint32_t>(2)));
    arr->push_back(new NymphType(static_cast<uint32_t>(3)));
    NymphType arr_val(arr, true);
    std::vector<NymphType*>* out_arr = arr_val.getArray();
    CHECK(out_arr != nullptr && out_arr->size() == 3, "NymphType array create+get");

    // Test 9: Shutdown
    bool shutdown_ok = NymphRemoteServer::shutdown();
    CHECK(shutdown_ok, "NymphRemoteServer::shutdown");

    if (g_fail) {
        std::printf("nymphrpc test failed %d items\n", g_fail);
        return 1;
    }
    std::printf("nymphrpc v0.1.1: all assertions passed\n");
    return 0;
}
