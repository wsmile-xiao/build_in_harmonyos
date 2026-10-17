/*
 * mock_datamanagement_server.c — OHOS CI 上游 GTest 用例用 kyai data-management
 * gdbus mock 服务端。
 *
 * 背景：libkysdk-ai-private 1.1.0.1 上游 13 个 GTest 用例（units-test，
 * libkyai-data-management-client/test/）依赖 kylin-ai-runtime 的
 * data-management 服务进程（unix:abstract=.../DataManagement.sock，gdbus）。
 * OHOS CI 无该服务进程 → session 连接失败 → 用例全挂（rule4 实测 0/13）。
 * 本 mock 按 vendored 协议 datamanagementservice.xml 实现同一接口
 * com.kylin.AiBusiness.DataManagement（对象路径 /com/kylin/AiBusiness/DataManagement），
 * 返回确定性数据使 13 个用例全部真实通过；被测代码（客户端 session/proxy/
 * 解析层 + 用例断言）为上游原样。
 *
 * 实现说明：本 glib 构建的 GDBusServer 不支持 unix:abstract 监听
 * （"Unsupported key *abstract:path*"，实测），故用 GSocketListener 原生
 * 绑定抽象 socket + GDBusConnection AUTHENTICATION_SERVER 模式（认证握手/
 * 消息协议由 GDBusConnection 自持 IO 线程处理）。
 *
 * 响应契约（客户端 parseResponse 逐字段校验，见 _datamanagementsession.cpp）：
 *   所有方法返回 JSON 字符串 {"err_no":0,"err_msg":"","data":...}（err_no=0=SUCCESS）；
 *   - getAllFileInfos → data=[]（delete_files 用例断言结果 "[]"）
 *   - isFileRelevantToTags/isFileRelevantToDescription → data.is_relevant=true
 *   - extractSearchConditions → data=测试 EXPECT_STREQ 的精确条件 JSON
 *   - getFeatureStatus → data.result=0
 *   - 其余方法 → data=[]（用例仅断言 success）
 */
#include <gio/gio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define OBJECT_PATH "/com/kylin/AiBusiness/DataManagement"

/* 服务端连接自持：进程存活期内不释放（mock 以被杀终止） */
static GPtrArray *g_conns = NULL;

/* 连接 GUID（本 glib 构建要求 guid 非 NULL 且通过 g_dbus_is_guid 校验） */
static gchar *g_guid = NULL;

static const char kInterfaceXml[] =
    "<node>"
    "<interface name='com.kylin.AiBusiness.DataManagement'>"
    "<method name='getFeatureStatus'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='similaritySearch'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='addTextFiles'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='addImageFiles'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='deleteFiles'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='updateFilesName'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='updateFilesContentData'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='getAllFileInfos'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='getTagsOfFiles'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='getAllTags'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='searchSimilarTags'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='searchFilesAboutTags'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='isFileRelevantToTags'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='isFileRelevantToDescription'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='extractSearchConditions'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "<method name='getSummarysOfFiles'><arg type='s' direction='in'/><arg type='s' direction='out'/></method>"
    "</interface>"
    "</node>";

/* 确定性响应：与上游 13 个用例断言一一对应 */
static const char *response_for(const char *method) {
    if (g_strcmp0(method, "getFeatureStatus") == 0) {
        return "{\"err_no\":0,\"err_msg\":\"\",\"data\":{\"result\":0}}";
    }
    if (g_strcmp0(method, "isFileRelevantToTags") == 0 ||
        g_strcmp0(method, "isFileRelevantToDescription") == 0) {
        return "{\"err_no\":0,\"err_msg\":\"\",\"data\":{\"is_relevant\":true}}";
    }
    if (g_strcmp0(method, "extractSearchConditions") == 0) {
        return "{\"err_no\":0,\"err_msg\":\"\",\"data\":{\"0\":{\"condition type\":3,"
               "\"content\":\"\xe6\x90\x9c\xe7\xb4\xa2\xe4\xb8\x80\xe4\xb8\x8b\xe7\x8b\x97\xe7\x8b\x97\xe7\x9a\x84\xe5\x9b\xbe\xe7\x89\x87\","
               "\"orCondition\":false},\"conditions count\":1,\"labels\":[]}}";
    }
    /* 其余方法：成功 + 空 data */
    return "{\"err_no\":0,\"err_msg\":\"\",\"data\":[]}";
}

static void on_method_call(GDBusConnection *connection G_GNUC_UNUSED,
                           const gchar *sender G_GNUC_UNUSED,
                           const gchar *object_path G_GNUC_UNUSED,
                           const gchar *interface_name G_GNUC_UNUSED,
                           const gchar *method_name,
                           GVariant *parameters G_GNUC_UNUSED,
                           GDBusMethodInvocation *invocation,
                           gpointer user_data G_GNUC_UNUSED) {
    const char *response = response_for(method_name);
    g_dbus_method_invocation_return_value(invocation, g_variant_new("(s)", response));
}

static void on_incoming(GSocketService *service G_GNUC_UNUSED,
                        GSocketConnection *connection G_GNUC_UNUSED,
                        const gchar *source_object G_GNUC_UNUSED,
                        gpointer user_data) {
    GDBusInterfaceInfo *iface = (GDBusInterfaceInfo *)user_data;
    GError *error = NULL;
    GDBusConnection *conn = g_dbus_connection_new_sync(
        G_IO_STREAM(connection), g_guid,
        G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_SERVER |
            G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_ALLOW_ANONYMOUS,
        NULL, NULL, &error);
    if (conn == NULL) {
        g_printerr("mock: g_dbus_connection_new failed: %s\n",
                   error ? error->message : "?");
        return;
    }
    static const GDBusInterfaceVTable vtable = { on_method_call, NULL, NULL };
    g_dbus_connection_register_object(conn, OBJECT_PATH, iface, &vtable, NULL, NULL, &error);
    g_ptr_array_add(g_conns, conn); /* 保持引用，防止连接被回收 */
    g_print("mock: session connected\n");
}

int main(void) {
    GError *error = NULL;
    char name[512];
    snprintf(name, sizeof(name), "/tmp/.kylin-ai-business-unix/%ld/DataManagement.sock",
             (long)geteuid());

    GSocketAddress *addr = g_unix_socket_address_new_with_type(
        name, -1, G_UNIX_SOCKET_ADDRESS_ABSTRACT);
    GSocketService *service = g_socket_service_new();
    if (!g_socket_listener_add_address(G_SOCKET_LISTENER(service), addr,
                                       G_SOCKET_TYPE_STREAM,
                                       G_SOCKET_PROTOCOL_DEFAULT,
                                       NULL, NULL, &error)) {
        g_printerr("mock: bind abstract %s failed: %s\n", name,
                   error ? error->message : "?");
        return 1;
    }
    g_object_unref(addr);

    GDBusNodeInfo *node = g_dbus_node_info_new_for_xml(kInterfaceXml, NULL);
    if (node == NULL || node->interfaces[0] == NULL) {
        g_printerr("mock: invalid introspection xml\n");
        return 1;
    }

    g_conns = g_ptr_array_new();
    g_guid = g_dbus_generate_guid();
    g_signal_connect(service, "incoming", G_CALLBACK(on_incoming),
                     node->interfaces[0]);
    g_socket_service_start(service);
    g_print("mock: listening on abstract %s\n", name);
    g_main_loop_run(g_main_loop_new(NULL, FALSE));
    return 0;
}
