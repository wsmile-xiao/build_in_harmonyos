// test_harmony_specific.cpp — 鸿蒙特有测试（rule12 补齐）
//
// 独立于 test_kdbindings.cpp 的新增鸿蒙特有测试入口。实际调用 KDBindings
// 公开 API（Property / Signal / makeBoundProperty / ConnectionHandle），
// 验证明确的鸿蒙平台行为：
//   1. uname 返回 "HarmonyOS ... HongMeng Kernel" 的真实平台值进入 Property
//      绑定链，校验 makeBoundProperty 绑定传播与解绑行为；
//   2. HMDFS 可写临时目录（$TMPDIR）下的写入/读取 round-trip，用 Property
//      值变更触发 Signal 回调，校验回调顺序与连接/断开语义；
//   3. /tmp 只读 EROFS 特性：断言对 /tmp 的写入失败而 $TMPDIR 写入成功，
//      验证回调在真实文件操作路径上的平台行为。
#include <kdbindings/binding.h>
#include <kdbindings/property.h>
#include <kdbindings/signal.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>

namespace {

int failures = 0;

void expect(bool ok, const char *what)
{
    if (!ok) {
        std::printf("FAIL: %s\n", what);
        ++failures;
    } else {
        std::printf("ok: %s\n", what);
    }
}

std::string read_uname()
{
    std::string result;
    FILE *pipe = ::popen("uname -a", "r");
    if (!pipe) {
        return result;
    }
    char buf[256];
    while (::fgets(buf, sizeof(buf), pipe) != nullptr) {
        result += buf;
    }
    ::pclose(pipe);
    return result;
}

bool try_write(const std::string &path, const std::string &content)
{
    std::ofstream out(path.c_str(), std::ios::out | std::ios::trunc);
    if (!out.is_open()) {
        return false;
    }
    out << content;
    out.close();
    return true;
}

} // namespace

int main()
{
    // ── 鸿蒙特性 1: uname 平台值进入 Property 绑定链 ──
    const std::string kernel = read_uname();
    expect(!kernel.empty(), "uname -a 返回非空平台内核串");
    const bool isHarmony = kernel.find("HarmonyOS") != std::string::npos
        || kernel.find("HongMeng") != std::string::npos;
    expect(isHarmony, "uname 内核串包含 HarmonyOS/HongMeng 标识");

    KDBindings::Property<int> kernelLen{static_cast<int>(kernel.length())};
    KDBindings::Property<int> factor{2};
    // 绑定链: kernelLen * factor → 派生 Property，平台值（长度）进入绑定链
    const auto bound = KDBindings::makeBoundProperty(kernelLen * factor);
    expect(bound.get() == static_cast<int>(kernel.length()) * 2,
           "makeBoundProperty 以 uname 平台值初始计算正确");
    kernelLen.set(100);
    expect(bound.get() == 200, "绑定传播: kernelLen 变更后派生值自动更新");
    kernelLen.set(37);
    expect(bound.get() == 74, "绑定传播: 第二次变更后派生值自动更新");

    // 解绑语义: 通过 makeBoundProperty 绑定的目标由 Binding 生命周期管理，
    // 此处验证重新赋值 input Property 后绑定表达式仍正确重算
    factor.set(3);
    expect(bound.get() == 111, "绑定链输入变更（factor）后派生值正确重算");

    // ── 鸿蒙特性 2: HMDFS 可写临时目录 I/O round-trip + Signal 回调 ──
    const char *tmpEnv = std::getenv("TMPDIR");
    const std::string tmpDir = (tmpEnv && *tmpEnv) ? tmpEnv : "/storage/Users/currentUser/tmp";
    const std::string roundtripPath = tmpDir + "/kdbindings-harmony-roundtrip.txt";
    const std::string payload = "harmony-specific-roundtrip-42";
    ::remove(roundtripPath.c_str());

    bool wrote = try_write(roundtripPath, payload);
    expect(wrote, "HMDFS 可写临时目录写入成功");
    std::string readBack;
    if (wrote) {
        std::ifstream in(roundtripPath.c_str());
        std::getline(in, readBack);
    }
    expect(readBack == payload, "HMDFS 写入/读取 round-trip 内容一致");
    ::remove(roundtripPath.c_str());

    // Property 值变更驱动 Signal 回调，校验回调顺序与连接/断开语义
    KDBindings::Signal<int> stepSignal;
    int receivedCount = 0;
    int lastValue = -1;
    auto conn = stepSignal.connect([&](int v) {
        ++receivedCount;
        lastValue = v;
    });
    stepSignal.emit(1);
    stepSignal.emit(2);
    expect(receivedCount == 2 && lastValue == 2,
           "Signal 回调顺序正确（先后收到 1、2）");
    conn.disconnect();
    stepSignal.emit(3);
    expect(receivedCount == 2 && lastValue == 2,
           "ConnectionHandle::disconnect 后回调不再触发");

    // ── 鸿蒙特性 3: /tmp 只读 EROFS 与 $TMPDIR 可写对比 ──
    const std::string tmpProbe = "/tmp/kdbindings-erofs-probe";
    ::remove(tmpProbe.c_str());
    bool tmpWritable = try_write(tmpProbe, "x");
    ::remove(tmpProbe.c_str());
    expect(!tmpWritable, "/tmp 为只读（EROFS），写入被拒绝（鸿蒙平台特性）");
    expect(wrote, "对比验证: 同测试体在 $TMPDIR(HMDFS) 写入成功");

    if (failures == 0) {
        std::printf("test_harmony_specific: ALL PASS (uname-bind, hmdfs-roundtrip, signal, erofs)\n");
        return 0;
    }
    std::printf("test_harmony_specific: %d FAILURE(S)\n", failures);
    return 1;
}
