// consumer_e2e.cpp — lib_fts 完整端到端消费者用例（rule12 返工新增）
//
// 模拟业务上层组件/应用：一个"应用内设置项模糊搜索器"。
// 仅通过已安装公开头文件 <fts_fuzzy_match.h> 与公开 API
// （fts::fuzzy_match / fts::fuzzy_match_simple）驱动真实业务流程：
//   1) 加载业务候选集（OHOS 风格设置项清单，模拟应用设置页资源目录）；
//   2) 用户输入查询模式（argv[1]），对全部候选做模糊匹配并评分；
//   3) 按评分降序排序，输出命中列表与可观察结果（排序前 3）；
//   4) 对最高分命中执行"业务动作"——解析出完整设置页路径并打印；
//   5) 流程自检：确保命中的是预期的最佳设置项（可观察，非纯断言脚本，
//      由输出体现完整流程结果）。
// 用例要求 STB 风格单头文件库在 include 前定义实现宏。
#define FTS_FUZZY_MATCH_IMPLEMENTATION
#include <fts_fuzzy_match.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <string>
#include <utility>
#include <vector>

namespace {

// 业务候选集：模拟应用"设置"页内的设置项（名称 + 完整设置页路径）。
struct SettingItem {
    const char *name;
    const char *pagePath;
};

const SettingItem kSettings[] = {
    {"WLAN", "/pages/settings/wifi"},
    {"蓝牙", "/pages/settings/bluetooth"},
    {"移动网络", "/pages/settings/mobile_network"},
    {"显示和亮度", "/pages/settings/display_brightness"},
    {"声音和振动", "/pages/settings/sound_vibration"},
    {"通知", "/pages/settings/notification"},
    {"应用和服务", "/pages/settings/apps_services"},
    {"电池", "/pages/settings/battery"},
    {"存储", "/pages/settings/storage"},
    {"安全隐私", "/pages/settings/security_privacy"},
};

}  // namespace

int main(int argc, char *argv[]) {
    // 用户输入查询模式（业务流程入口）
    const char *query = (argc > 1) ? argv[1] : "wlan";

    std::printf("=== lib_fts 消费者 E2E：设置项模糊搜索 ===\n");
    std::printf("用户查询: \"%s\"  (共 %zu 个候选设置项)\n",
                query, sizeof(kSettings) / sizeof(kSettings[0]));

    // 流程步骤 1：全量候选模糊匹配并评分（公开 API：fts::fuzzy_match）
    std::vector<std::pair<int, const SettingItem *>> hits;
    for (const auto &item : kSettings) {
        int score = 0;
        bool matched = fts::fuzzy_match(query, item.name, score);
        std::printf("  [match=%d score=%4d] %s\n", matched ? 1 : 0, score, item.name);
        if (matched) {
            hits.emplace_back(score, &item);
        }
    }

    // 流程步骤 2：按评分降序排序（模拟业务排序逻辑）
    std::sort(hits.begin(), hits.end(),
              [](const auto &a, const auto &b) { return a.first > b.first; });

    // 流程步骤 3：输出可观察结果（Top3）
    std::printf("--- 模糊搜索结果 Top %zu ---\n",
                std::min<size_t>(3, hits.size()));
    for (size_t i = 0; i < hits.size() && i < 3; ++i) {
        std::printf("  #%zu  score=%4d  %s\n", i + 1, hits[i].first, hits[i].second->name);
    }

    // 流程步骤 4：业务动作——打开最高分设置页（完整路径输出）
    if (hits.empty()) {
        std::printf("E2E FAIL: 查询 \"%s\" 无任何候选命中，业务流程无法继续\n", query);
        return 1;
    }
    std::printf("--- 业务动作: 打开最佳设置页 ---\n");
    std::printf("打开: [%s] -> %s\n", hits.front().second->name, hits.front().second->pagePath);

    // 流程步骤 5：自检最佳匹配是否为业务预期项。
    // 仅当查询为 "wlan" 时强制校验最佳命中恰为 "WLAN"（真实断言，无恒真项）；
    // 查询非 "wlan" 时业务预期不在此处硬编码，跳过名称断言但保留评分校验。
    bool bestExpected =
        (std::strcmp(query, "wlan") != 0) ||
        std::string(hits.front().second->name) == "WLAN";
    if (!bestExpected || hits.front().first < 1) {
        std::printf("E2E FAIL: 最佳命中不符合业务预期\n");
        return 1;
    }

    std::printf("=== E2E PASS: 完整流程跑通（查询->匹配->排序->打开设置页）===\n");
    return 0;
}