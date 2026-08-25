/* test_package/test.cpp — avisynthplus 3.7.5 consumer test (R34 合规)
 *
 * L1 test:
 * 1. 编译并链接 libavisynth（含头文件与库）——真实调用 API；
 * 2. 运行时 CreateScriptEnvironment 创建 AviSynth 环境（真实执行库代码），
 *    IScriptEnvironment::CheckVersion 校验接口版本（版本不匹配抛
 *    AvisynthError）——即为真实断言；
 * 3. 释放环境（env->DeleteScriptEnvironment）。
 */
#include <avisynth/avisynth.h>
#include <cstdio>

int main() {
    int interface_version = AVISYNTH_INTERFACE_VERSION;
    /* 真实调用 libavisynth：创建脚本环境（导出符号
     * CreateScriptEnvironment，链接期即验证库存在） */
    IScriptEnvironment *env = CreateScriptEnvironment(interface_version);
    if (env == nullptr) {
        std::printf("avisynthplus 3.7.5 consumer test FAILED: "
                    "CreateScriptEnvironment returned null\n");
        return 1;
    }
    /* 真实调用库方法：CheckVersion 校验接口版本（不匹配抛异常——
     * 断言失败即程序非零退出） */
    bool ok = true;
    try {
        env->CheckVersion(interface_version);
    } catch (const AvisynthError &e) {
        std::printf("avisynthplus 3.7.5 consumer test FAILED: "
                    "CheckVersion: %s\n", e.msg);
        ok = false;
    }
    env->DeleteScriptEnvironment();
    if (!ok) {
        return 1;
    }
    std::printf("avisynthplus 3.7.5 consumer test OK (CreateScriptEnvironment "
                "v%d + CheckVersion)\n", interface_version);
    return 0;
}
