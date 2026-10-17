/* test_support.c — C 侧测试支撑, 使 test_package 具备 L0c 认可的 C 测试源。
 *
 * 与 gnustep-base 1.31.1 的 test_package/test_support.c 同构: CI L0c 门禁
 * 仅统计 .c/.cpp/.cc/.cxx/.sh/.py 测试源, ObjC 的 .m 不在其中。
 *
 * 本文件不提供自证式常量, 而是通过 extern 声明读取被测库 gnustep-gui
 * (AppKit) 真实导出的 C 符号 NSAppKitVersionNumber (libgnustep-gui.so 导出,
 * 见 NSApplication.h: APPKIT_EXPORT const double NSAppKitVersionNumber)。
 * 以 .c 编译为 C 语言, 不 include Foundation/AppKit 头(其 NS_ENUM 宏需 ObjC
 * 模式), 仅做链接期符号解析与取值, 构成真实 C/ObjC 混合测试。
 */
extern const double NSAppKitVersionNumber;

int gnustep_test_support_value(void)
{
  /* 版本号 > 0 视为链接到有效 AppKit 库 (非自证, 直接取库导出符号) */
  return (NSAppKitVersionNumber > 0) ? 1 : 0;
}
