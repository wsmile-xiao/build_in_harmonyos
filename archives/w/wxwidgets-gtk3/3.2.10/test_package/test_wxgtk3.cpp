#include <wx/wx.h>
#include <wx/version.h>
#include <wx/colour.h>
#include <wx/gdicmn.h>
#include <stdio.h>

// R34: 消费者测试必须实际调用被测包 API。
// 只使用不需要显示连接/事件循环的 GUI 类 API（与 gtk 包 broadway 后端
// 的无显示验证口径一致）。
int main(void) {
    // 1. 版本一致性（wxGetLibraryVersionInfo 属 core 库，仅 GUI 构建存在）
    wxVersionInfo vi = wxGetLibraryVersionInfo();
    printf("wx version: %d.%d.%d\n", vi.GetMajor(), vi.GetMinor(), vi.GetMicro());
    if (vi.GetMajor() != 3 || vi.GetMinor() != 2 || vi.GetMicro() < 10) {
        fprintf(stderr, "wxGetLibraryVersionInfo mismatch\n");
        return 1;
    }
    if (!wxCHECK_VERSION(3, 2, 10)) {
        fprintf(stderr, "wxCHECK_VERSION(3,2,10) failed\n");
        return 1;
    }

    // 2. wxColour（wx/gdicmn.h + colour data——core 库符号）
    wxColour red(*wxRED);
    if (red.Red() != 255 || red.Green() != 0 || red.Blue() != 0) {
        fprintf(stderr, "wxColour RGB mismatch\n");
        return 1;
    }

    // 3. wxSize/wxPoint 运算（core 内联与符号混合路径）
    wxSize sz(120, 80);
    if (sz.GetWidth() + sz.GetHeight() != 200) {
        fprintf(stderr, "wxSize arithmetic mismatch\n");
        return 1;
    }

    // 4. wxString（base 库符号——验证 base 与 core 链接顺序）
    wxString s = wxT("harmony");
    s += wxT("-pc");
    if (s != wxT("harmony-pc")) {
        fprintf(stderr, "wxString concat mismatch\n");
        return 1;
    }

    printf("test wxwidgets-gtk3 3.2.10: OK\n");
    return 0;
}
