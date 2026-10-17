// test_package 消费者测试：通过 lldb 公开 SB API 实际调用被测包
// （SBDebugger::Create / SBTarget::CreateTarget / SBModule::GetNumSymbols），
// 验证第三方消费者可编译、链接、调用并正常运行。
#include <lldb/API/SBDebugger.h>
#include <lldb/API/SBTarget.h>
#include <lldb/API/SBModule.h>
#include <lldb/API/SBStream.h>
#include <cstdio>
#include <string>

int main(int argc, char **argv) {
    bool self_check = (argc > 1 && std::string(argv[1]) == "--self-check");
    lldb::SBDebugger::Initialize();
    lldb::SBDebugger dbg = lldb::SBDebugger::Create();
    if (!dbg.IsValid()) {
        std::fprintf(stderr, "FAIL: SBDebugger::Create invalid\n");
        lldb::SBDebugger::Terminate();
        return 1;
    }
    dbg.SetAsync(false);

    // 自检模式：无法定位外部程序时仅验证调试器实例化成功；常规模式加载 /bin/ls。
    const char *prog = "/bin/ls";
    if (self_check) {
        std::printf("test_package OK: SBDebugger created (version %s)\n",
                    dbg.GetVersionString());
        lldb::SBDebugger::Destroy(dbg);
        lldb::SBDebugger::Terminate();
        return 0;
    }
    lldb::SBTarget target = dbg.CreateTarget(prog);
    if (!target.IsValid()) {
        std::fprintf(stderr, "FAIL: CreateTarget %s\n", prog);
        lldb::SBDebugger::Terminate();
        return 1;
    }
    lldb::SBModule module = target.GetModuleAtIndex(0);
    std::printf("test_package OK: target_module=%s module_symbols=%llu\n",
                module.GetFileSpec().GetFilename(),
                static_cast<unsigned long long>(module.GetNumSymbols()));
    lldb::SBDebugger::Destroy(dbg);
    lldb::SBDebugger::Terminate();
    return 0;
}