// 消费者冒烟 2（审查 P2）：实际调用 kylin_ai_generate_gdbus_proto_code 生成的
// glue 函数——验证宏生成链路、KYLAI_GDBUS_CODEGEN / KYLAI_GDBUS_PROTOCOL_DIR
// 变量注入与 gdbus-codegen 依赖真实生效（编译 + 链接 + 执行）。
// 调用 interface_info() 做纯内存查询（不连接 D-Bus）：proxy_new_sync 需要
// GDBusConnection，CI/app 环境无 session bus 会阻塞，interface_info 返回的
// 接口名同时验证协议 XML 内容正确（com.kylin.AiRuntime.CoreSpeechService）。
#include "corespeechserviceglue.h"

#include <gio/gio.h>
#include <glib.h>

int main() {
    GDBusInterfaceInfo *info = ai_runtime_core_speech_service_interface_info();
    if (info == nullptr || info->name == nullptr) {
        return 1;
    }
    if (g_strcmp0(info->name, "com.kylin.AiRuntime.CoreSpeechService") != 0) {
        return 1;
    }
    return 0;
}
