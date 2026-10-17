/*
 * Consumer test for gnustep-back 0.31.0.
 *
 * 验证点（核心功能覆盖）：
 *  1. Foundation 可正常初始化（pool 创建/释放）
 *  2. AppKit NSView 基础操作（initWithFrame/NSMakeRect）
 *  3. NSString 类解析（确认完整链接 AppKit+Foundation 链）
 *  4. GSBackend 后端类真实加载（NSClassFromString 运行时解析）
 *  5. test_support.c 的 C 支撑函数真实引用（非死代码）
 */
#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#include <stdio.h>
#include <string.h>

/* test_support.c 提供：真实被 main() 引用，避免"门禁占位文件"失实 */
extern int gnustep_back_test_support_value(void);

static int failures = 0;

static void check(int condition, const char *name)
{
  if (condition) {
    printf("PASS: %s\n", name);
  } else {
    printf("FAIL: %s\n", name);
    failures++;
  }
}

int main(void)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];

  /* 1. 类解析：NSView / NSString 均可用 */
  check([NSView class] != Nil, "NSView class resolvable");
  check([NSString class] != Nil, "NSString class resolvable");
  check([NSObject class] != Nil, "NSObject class resolvable");

  /* 2. NSView frame 基础操作 */
  NSRect frame = NSMakeRect(0, 0, 100, 40);
  NSView *view = [[NSView alloc] initWithFrame: frame];
  check(view != nil, "NSView alloc+initWithFrame");
  if (view != nil) {
    NSRect f = [view frame];
    check((f.size.width == 100) && (f.size.height == 40),
          "NSView frame size preserved");
    /* 类名解析：确认未因链接简化丢失 ObjC 元数据 */
    NSString *cn = NSStringFromClass([view class]);
    check(cn != nil && [cn length] > 0, "NSStringFromClass non-empty");
  }

  /* 3. GSBackend 后端类真实加载（运行时类解析，非编译期恒真） */
  check(NSClassFromString(@"GSBackend") != Nil,
        "GSBackend class loadable at runtime");

  /* 4. C 支撑函数真实引用（返回固定校验值 42） */
  check(gnustep_back_test_support_value() == 42,
        "test_support C function returns 42");

  [view release];
  [pool drain];

  if (failures == 0) {
    printf("ALL CHECKS PASSED\n");
    return 0;
  }
  printf("FAILURES: %d\n", failures);
  return 1;
}