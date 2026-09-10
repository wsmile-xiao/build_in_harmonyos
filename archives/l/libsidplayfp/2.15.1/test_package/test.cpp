#include <cstdio>
#include "sidplayfp/sidplayfp.h"
#include "sidplayfp/SidConfig.h"
#include "sidplayfp/SidInfo.h"

// 真实消费者验证：实例化播放器、读取库版本信息、配置并检查错误状态
int main() {
    sidplayfp player;
    const SidInfo &info = player.info();

    const char *name = info.name();
    const char *version = info.version();
    std::printf("libsidplayfp name=%s version=%s\n",
                name ? name : "(null)", version ? version : "(null)");
    if (!name || !version) {
        std::printf("FAIL: info.name()/version() 为空\n");
        return 1;
    }

    SidConfig cfg;
    cfg.defaultC64Model = SidConfig::PAL;
    cfg.forceC64Model = false;
    cfg.defaultSidModel = SidConfig::MOS6581;

    if (!player.config(cfg)) {
        const char *err = player.error();
        std::printf("FAIL: config() 失败: %s\n", err ? err : "(null)");
        return 1;
    }
    if (player.config().defaultC64Model != SidConfig::PAL) {
        std::printf("FAIL: config() 未应用 PAL 模型\n");
        return 1;
    }

    std::printf("libsidplayfp consumer test: OK\n");
    return 0;
}
