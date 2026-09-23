/* HarmonyOS 专项功能测试 — open62541/1.5.7 消费者验证
 *
 * 真实 server + client 闭环：
 *   1. 用打包的 libopen62541 在 opc.tcp://127.0.0.1:<PORT> 启动真实 UA_Server，
 *      并发布一个命名空间 1 的 Int32 变量节点（初值 42）。
 *   2. 用打包库的 UA_Client 经 TCP loopback 连接该 server。
 *   3. 读取节点 -> 必须为 42；写入 43 -> 再读 -> 必须为 43。
 *
 * 任一环节失败立即非零退出。该测试不依赖显示/外设，仅使用 loopback TCP，
 * 是 OHOS 平台上对打包库的最小真实功能面验证。
 *
 * 注意（open62541 1.5.7 API）：
 *   - 节点 ID 常量是 UA_NS0ID_*（nodeids.h），不是旧版 UA_IDS_*；
 *   - 服务端配置用 UA_ServerConfig_setMinimal(scfg, port, NULL)（旧版
 *     UA_ServerConfig_set_port 已移除）；
 *   - 客户端配置用 UA_ClientConfig_setDefault(&ccfg)，endpoint 由
 *     UA_Client_connect(client, url) 直接传入（无 UA_ClientConfig_set_endpoint）；
 *   - 状态码判定是函数 UA_StatusCode_isBad()（UA_STATUSCODE_ISBAD 宏已移除）；
 *   - 清理用 UA_Variant_clear()（UA_Variant_cleanup 已移除）。
 */
#include <open62541/client.h>
#include <open62541/client_highlevel.h>
#include <open62541/client_config_default.h>
#include <open62541/server.h>
#include <open62541/server_config_default.h>
#include <open62541/types_generated.h>
#include <open62541/nodeids.h>

#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#define PORT    48431
#define VAR_NS  1
#define VAR_IDX 61001

static volatile UA_Boolean serverRunning = true;

/* open62541 的 server 事件循环需要被持续驱动：run_startup 只做启动，
 * 之后必须在后台线程循环调用 run_iterate（上游测试同款模式），
 * 否则 client 的 TCP 连接无人受理，UA_Client_connect 会超时。 */
static void *serverLoop(void *arg) {
    UA_Server *srv = (UA_Server *)arg;
    while(serverRunning)
        UA_Server_run_iterate(srv, true);
    return NULL;
}

static void fail(const char *msg) {
    fprintf(stderr, "FAIL: %s\n", msg);
    exit(1);
}

int main(void) {
    /* 1. 真实 server（loopback TCP） */
    UA_Server *server = UA_Server_new();
    UA_ServerConfig *scfg = UA_Server_getConfig(server);
    if(UA_StatusCode_isBad(UA_ServerConfig_setMinimal(scfg, PORT, NULL)))
        fail("UA_ServerConfig_setMinimal");

    UA_Variant seed;
    UA_Int32 seedVal = 42;
    UA_Variant_init(&seed);
    UA_Variant_setScalar(&seed, &seedVal, &UA_TYPES[UA_TYPES_INT32]);

    UA_NodeId varId = UA_NODEID_NUMERIC(VAR_NS, VAR_IDX);
    UA_VariableAttributes attr;
    UA_VariableAttributes_init(&attr);
    /* 变量节点的数据类型、ValueRank 与访问级别必须在建节点时声明：
     * 默认 UA_VariableAttributes_init 的 accessLevel=0，会话对该节点
     * 的读取会直接返回 BadUserAccessDenied；显式放开读写掩码。 */
    attr.dataType = UA_TYPES[UA_TYPES_INT32].typeId;
    attr.valueRank = UA_VALUERANK_SCALAR;
    attr.accessLevel = UA_ACCESSLEVELMASK_READ | UA_ACCESSLEVELMASK_WRITE;
    UA_StatusCode ret = UA_Server_addVariableNode(
        server, varId,
        UA_NODEID_NUMERIC(0, UA_NS0ID_OBJECTSFOLDER),
        UA_NODEID_NUMERIC(0, UA_NS0ID_HASCOMPONENT),
        UA_QUALIFIEDNAME(1, "ohosTestVar"),
        UA_NODEID_NUMERIC(0, UA_NS0ID_BASEDATAVARIABLETYPE),
        attr, NULL, NULL);
    if(UA_StatusCode_isBad(ret))
        fail("UA_Server_addVariableNode");
    /* 1.5.7 的 addVariableNode 无初值参数：节点建好后用 writeValue 写入初值 42 */
    ret = UA_Server_writeValue(server, varId, seed);
    if(UA_StatusCode_isBad(ret))
        fail("UA_Server_writeValue (initial 42)");
    ret = UA_Server_run_startup(server);
    if(UA_StatusCode_isBad(ret))
        fail("UA_Server_run_startup");
    pthread_t serverThread;
    if(pthread_create(&serverThread, NULL, serverLoop, server) != 0)
        fail("pthread_create(serverLoop)");
    printf("[server] listening on opc.tcp://127.0.0.1:%d\n", PORT);

    /* 2. 真实 client 经 TCP loopback 连接 */
    char endpoint[64];
    snprintf(endpoint, sizeof endpoint, "opc.tcp://127.0.0.1:%d", PORT);

    UA_Client *client = UA_Client_new();
    UA_ClientConfig ccfg;
    UA_ClientConfig_setDefault(&ccfg);
    ret = UA_Client_connect(client, endpoint);
    if(UA_StatusCode_isBad(ret))
        fail("UA_Client_connect");
    printf("[client] connected\n");

    /* 3. 读：必须为 42 */
    UA_Variant value;
    UA_Variant_init(&value);
    ret = UA_Client_readValueAttribute(client, varId, &value);
    if(UA_StatusCode_isBad(ret)) {
        fprintf(stderr, "read #1 status: 0x%08X (%s)\n", ret,
                UA_StatusCode_name(ret));
        fail("UA_Client_readValueAttribute #1");
    }
    if(value.type != &UA_TYPES[UA_TYPES_INT32] || value.data == NULL)
        fail("read #1: unexpected type");
    if(*(UA_Int32 *)value.data != 42)
        fail("read #1: value != 42");
    printf("[client] read #1 = 42  OK\n");

    /* 4. 写 43，回读必须为 43 */
    UA_Int32 newVal = 43;
    UA_Variant writeVal;
    UA_Variant_init(&writeVal);
    UA_Variant_setScalar(&writeVal, &newVal, &UA_TYPES[UA_TYPES_INT32]);
    ret = UA_Client_writeValueAttribute(client, varId, &writeVal);
    if(UA_StatusCode_isBad(ret))
        fail("UA_Client_writeValueAttribute");
    UA_Variant readback;
    UA_Variant_init(&readback);
    ret = UA_Client_readValueAttribute(client, varId, &readback);
    if(UA_StatusCode_isBad(ret))
        fail("UA_Client_readValueAttribute #2");
    if(readback.type != &UA_TYPES[UA_TYPES_INT32] ||
       *(UA_Int32 *)readback.data != 43)
        fail("read #2: value != 43");
    printf("[client] write 43 / read #2 = 43  OK\n");

    UA_Variant_clear(&value);
    UA_Variant_clear(&readback);
    UA_Client_disconnect(client);
    UA_Client_delete(client);
    /* 停止事件循环线程并回收，随后正常关闭 server */
    serverRunning = false;
    pthread_join(serverThread, NULL);
    UA_Server_run_shutdown(server);
    UA_Server_delete(server);
    printf("PASS: open62541 HarmonyOS functional test (real server+client over loopback)\n");
    return 0;
}
