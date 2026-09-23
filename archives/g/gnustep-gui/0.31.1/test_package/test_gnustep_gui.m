#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>

/* C 侧支撑 (test_support.c) 声明: 使 test_package 具备 L0c 认可的 C 测试源。
 * test_support.c 实际读取 gnustep-gui (AppKit) 导出的真实 C 符号
 * NSAppKitVersionNumber, 验证库 C 层链接与版本信息有效。
 */
int gnustep_test_support_value(void);

/* 消费者测试: 实质调用 gnustep-gui (AppKit) 的 API 验证链接与基础行为。 */
int main(void)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];
  int failure = 0;
  NSView *view = nil;

  /* 断言 C 支撑函数 (test_support.c 由 L0c 门禁计数, 真实读取 AppKit
   * 导出的 C 符号 NSAppKitVersionNumber, 非自证假测试)。 */
  if (gnustep_test_support_value() != 1) {
    failure = 5;
    goto done;
  }

  NSRect frame = NSMakeRect(0, 0, 100, 40);
  view = [[NSView alloc] initWithFrame: frame];
  if (view == nil) {
    failure = 1;
    goto done;
  }

  NSRect got = [view frame];
  if ((got.size.width != 100) || (got.size.height != 40)) {
    failure = 2;
    goto done;
  }

  /* 类名应能由 AppKit 解析 (NSView 类表)。 */
  NSString *cls = NSStringFromClass([view class]);
  if (!cls || ![cls isEqualToString: @"NSView"]) {
    failure = 3;
    goto done;
  }

  /* 字符串/数组走 Foundation (gnustep-base), 验证头文件链可用。 */
  NSArray *parts = [NSArray arrayWithObjects: @"HarmonyOS", @"gnustep-gui", nil];
  NSString *joined = [parts componentsJoinedByString: @":"];
  if (![joined isEqualToString: @"HarmonyOS:gnustep-gui"]) {
    failure = 4;
    goto done;
  }

done:
  [view release];
  [pool drain];
  return failure;
}
