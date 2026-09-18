// 消费者冒烟测试：真实 include 并使用 KylinAiEngine 头库 API（R34 要求）。
// AbstractAiEngine 派生类 + engineName() 覆盖 + AiEngineResult 构造，
// 验证头文件可用、C++17 编译通过、链接 KylinAiEngine::KylinAiEngine。
#include <kylin-ai/ai-engine/aiengine.h>
#include <kylin-ai/ai-engine/aiengineresult.h>

#include <cassert>
#include <string>

using namespace ai_engine;

namespace {

class FakeEngine : public AbstractAiEngine {
public:
    std::string engineName() const override { return "test-engine"; }
    bool isCloud() const override { return false; }
    bool isBuiltInEngine() const override { return false; }
    bool isCustomModelEngine() const override { return true; }
    std::string modelInfo() const override { return "{}"; }
};

}  // namespace

int main() {
    FakeEngine engine;
    assert(engine.engineName() == "test-engine");
    assert(!engine.isCloud());
    assert(!engine.isBuiltInEngine());
    assert(engine.isCustomModelEngine());
    assert(engine.currentModel().empty());

    ai_engine::result::AiEngineBaseResult result;
    (void)result;
    return 0;
}
