// test_package for mygui — real consumer-side validation (R34).
// Compiles against MyGUI headers and links MyGUIEngine, calls a real API
// (version macros + LogManager singleton) so the link is a real dependency.
#include <MyGUI.h>

#include <cstdio>

int main() {
    // Version macros are resolved from MyGUI_Prerequest.h (real header usage).
    std::printf("MyGUI %d.%d.%d\n", MYGUI_VERSION_MAJOR, MYGUI_VERSION_MINOR,
                MYGUI_VERSION_PATCH);

    // LogManager::getInstance() is a real exported symbol of MyGUIEngine —
    // forces the consumer link to genuinely depend on the package (R34).
    MyGUI::LogManager* lm = MyGUI::LogManager::getInstancePtr();
    if (lm) {
        lm->log("MyGUI.test", MyGUI::LogLevel::Info, "test_package link OK",
                __FILE__, __LINE__);
        std::printf("MyGUI LogManager ok\n");
    } else {
        std::printf("MyGUI LogManager null (no instance created)\n");
    }

    std::printf("mygui test_package PASS\n");
    return 0;
}
