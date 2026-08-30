// test_headless.cpp — mygui 3.4.4 headless-consumer functional tests (r11).
//
// Purpose: exercise real MyGUI behaviour WITHOUT a display or real renderer,
// using the Dummy platform (RENDERSYSTEM=1) + the r10-fixed resource
// registration path in DummyDataManager.  Each test asserts an outcome; it
// does NOT merely print initialization, and it does not require a window.
//
// Covered behaviours:
//   T1  resource registration + isDataExist (positive)
//   T2  getDataPath resolves to the registered file (full-path lookup)
//   T3  getData returns a stream whose content matches the file
//   T4  recursive addResourceLocation finds nested files
//   T5  deterministic missing-resource behaviour: isDataExist=false,
//       getDataPath empty, getData nullptr
//   T6  getDataListNames pattern filtering (positive + negative)
//
// Build/CMake: declared in test_package/CMakeLists.txt as test_headless.
// Formal runenv: sourced from the conan runenv script; cwd = bin dir.

#include <MyGUI.h>
#include <MyGUI_DummyPlatform.h>
#include <MyGUI_DummyDataManager.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <unistd.h>

static int g_fail = 0;
static int g_pass = 0;

static void check(bool ok, const char* name)
{
    if (ok) { g_pass++; std::printf("PASS %s\n", name); }
    else { g_fail++; std::printf("FAIL %s\n", name); }
}

// Create a throwaway resource tree under <tmp>/mygui-hl-<pid>/
static std::string make_tree()
{
    std::string dir = "/storage/Users/currentUser/tmp/mygui-hl-";
    char pid[32];
    std::snprintf(pid, sizeof(pid), "%d", (int)getpid());
    dir += std::to_string(getpid());
    // ensure dirs exist
    std::string mk = "mkdir -p \"" + dir + "/sub\"";
    if (std::system(mk.c_str()) != 0) return "";
    {
        std::ofstream f(dir + "/present.txt");
        f << "hello-myGUI-headless";
    }
    {
        std::ofstream f(dir + "/sub/nested.txt");
        f << "nested-content";
    }
    return dir;
}

int main()
{
    // T0: version sanity (real header macros)
    check(MYGUI_VERSION_MAJOR == 3 && MYGUI_VERSION_MINOR == 4 &&
              MYGUI_VERSION_PATCH == 4,
          "T0 version macros 3.4.4");

    // The Dummy platform owns the DataManager singleton used by the package;
    // instantiating it registers DummyDataManager as the active DataManager.
    MyGUI::DummyPlatform platform;

    MyGUI::DummyDataManager* dm = MyGUI::DummyDataManager::getInstancePtr();
    check(dm != nullptr, "T0 DummyDataManager singleton available");

    std::string tree = make_tree();
    check(!tree.empty(), "T0 temp resource tree created");

    // T1: register non-recursive location, positive isDataExist
    dm->addResourceLocation(tree, false);
    check(dm->isDataExist("present.txt"), "T1 isDataExist positive");

    // T2: getDataPath resolves full path to the registered file
    std::string p = dm->getDataPath("present.txt");
    check(p.size() > strlen("present.txt") &&
              p.compare(p.size() - strlen("present.txt"), std::string::npos, "present.txt") == 0,
          "T2 getDataPath resolves registered file");

    // T3: getData returns content stream matching the file
    MyGUI::IDataStream* st = dm->getData("present.txt");
    check(st != nullptr, "T3 getData non-null");
    if (st) {
        // r13: 适配 MyGUI DataStream::read() 的既有契约——它返回
        // min(size(), _count) 而非实际读取字节（EOF 后仍返回 size()），
        // read-until-0 循环会在 EOF 后无限自旋（r12 实测 SIGKILL/Error 137）。
        // 改为按 size() 一次读取，确定性断言内容匹配，语义与上游一致。
        std::string content;
        const size_t total = st->size();
        if (total > 0) {
            content.resize(total);
            st->read(&content[0], total);
        }
        dm->freeData(st);
        check(content == "hello-myGUI-headless", "T3 getData content match");
    }

    // T4: recursive registration finds nested file
    // r13: mask 用 basename "nested.txt"（非子路径 "sub/nested.txt"）——
    // DataManager 的 scanFolder 递归用同一 mask 对每层 d_name 做 fnmatch，
    // 含 '/' 的 mask 无法匹配任何单层名字（r13 实测 T4 失败后修正）。
    MyGUI::DummyDataManager* dm2 = MyGUI::DummyDataManager::getInstancePtr();
    dm2->addResourceLocation(tree, true);
    check(dm->isDataExist("nested.txt"), "T4 recursive path isDataExist");
    check(dm->getDataPath("nested.txt").find("nested.txt") != std::string::npos,
          "T4 recursive getDataPath");

    // T5: deterministic missing-resource behaviour
    check(!dm->isDataExist("absent-file-xyz.txt"), "T5 missing isDataExist=false");
    check(dm->getDataPath("absent-file-xyz.txt").empty(), "T5 missing getDataPath empty");
    check(dm->getData("absent-file-xyz.txt") == nullptr, "T5 missing getData nullptr");

    // T6: getDataListNames positive/negative pattern
    const MyGUI::VectorString& names = dm->getDataListNames("present.txt");
    bool found = false;
    for (const auto& s : names) {
        if (s.find("present.txt") != std::string::npos) found = true;
    }
    check(found, "T6 getDataListNames positive");
    check(dm->getDataListNames("no-such-pattern-*.bin").empty(), "T6 getDataListNames negative");

    std::printf("RESULT %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}