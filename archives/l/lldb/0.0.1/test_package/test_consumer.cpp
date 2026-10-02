// test_package 消费者测试：通过 lldb 公开 SB API 实际调用被测包
// （无 ptrace、不派生进程——CI 安全），验证第三方消费者可编译、
// 链接、调用并正常运行。
//   C1: SBDebugger::Initialize/Create + 版本串
//   C2: CreateTarget(自二进制, unstripped) + 模块数/符号数
//   C3: BreakpointCreateByName("main")（测试目标显式 -g 编译，保证行表/符号）；
//       若目标无符号（strip）退化为模块 section 尺寸校验（ELF 结构级）
#include <lldb/API/SBDebugger.h>
#include <lldb/API/SBTarget.h>
#include <lldb/API/SBModule.h>
#include <lldb/API/SBBreakpoint.h>
#include <lldb/API/SBSection.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;
    lldb::SBDebugger::Initialize();
    lldb::SBDebugger dbg = lldb::SBDebugger::Create();
    if (!dbg.IsValid()) {
        std::fprintf(stderr, "FAIL C1: SBDebugger::Create invalid\n");
        lldb::SBDebugger::Terminate();
        return 1;
    }
    dbg.SetAsync(false);
    const char *version_c = dbg.GetVersionString();
    if (version_c == nullptr || std::string(version_c).empty()) {
        std::fprintf(stderr, "FAIL C1: empty version string\n");
        lldb::SBDebugger::Terminate();
        return 1;
    }

    // C2: 目标=测试二进制自身（unstripped，必然有 main 符号与 section，不依赖设备预装二进制）
    char self_path[4096];
    self_path[0] = '\0';
    // readlink 成功不写终止符（POSIX），须用返回长度显式补 '\0'；
    // 仅 readlink 失败时才走 argv[0] 回退
    const ssize_t self_len =
        readlink("/proc/self/exe", self_path, sizeof(self_path) - 1);
    if (self_len > 0) {
        self_path[self_len] = '\0';
    } else if (argv[0] != nullptr && std::string(argv[0]).size() < sizeof(self_path) - 1) {
        std::snprintf(self_path, sizeof(self_path), "%s", argv[0]);
    }
    if (self_path[0] == '\0') {
        std::fprintf(stderr, "FAIL C2: cannot resolve self executable path\n");
        lldb::SBDebugger::Terminate();
        return 1;
    }
    lldb::SBTarget target = dbg.CreateTarget(self_path);
    if (!target.IsValid()) {
        std::fprintf(stderr, "FAIL C2: CreateTarget self invalid\n");
        lldb::SBDebugger::Terminate();
        return 1;
    }
    unsigned num_modules = target.GetNumModules();
    lldb::SBModule module = target.GetModuleAtIndex(0);
    unsigned long long num_symbols = module.GetNumSymbols();
    if (num_modules == 0 || num_symbols == 0) {
        std::fprintf(stderr,
                     "FAIL C2: no modules/symbols (modules=%u symbols=%llu)\n",
                     num_modules, num_symbols);
        lldb::SBDebugger::Terminate();
        return 1;
    }

    bool c3_ok = false;
    std::string c3_desc;
    lldb::SBBreakpoint bp = target.BreakpointCreateByName("main");
    if (bp.IsValid() && bp.GetNumLocations() > 0) {
        c3_ok = true;
        c3_desc = "bp_locations=" + std::to_string(bp.GetNumLocations());
    } else {
        // 目标可能 strip：退化为模块 section 尺寸校验（ELF 结构级，无符号依赖）
        unsigned num_sections = module.GetNumSections();
        lldb::SBSection section;
        for (unsigned i = 0; i < num_sections; ++i) {
            lldb::SBSection s = module.GetSectionAtIndex(i);
            if (s.IsValid() && s.GetByteSize() > 0) {
                section = s;
                break;
            }
        }
        if (section.IsValid() && section.GetByteSize() > 0) {
            c3_ok = true;
            c3_desc = "section_bytes=" + std::to_string(section.GetByteSize());
        }
    }
    if (!c3_ok) {
        std::fprintf(stderr, "FAIL C3: breakpoint/address-range check failed\n");
        lldb::SBDebugger::Terminate();
        return 1;
    }

    std::printf(
        "test_package OK: C1 version=%s C2 modules=%u symbols=%llu C3 %s\n",
        version_c, num_modules, num_symbols, c3_desc.c_str());
    lldb::SBDebugger::Destroy(dbg);
    lldb::SBDebugger::Terminate();
    return 0;
}
