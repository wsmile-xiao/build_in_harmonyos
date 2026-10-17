/*
 * Consumer test for GNUstep Performance 0.6.0.
 *
 * 验证点（核心功能覆盖）：
 *  1. Foundation 可正常初始化（pool 创建/释放）
 *  2. GSCache 缓存核心操作（setObject:forKey: / objectForKey:）
 *  3. GSTicker 类可加载（NSClassFromString 运行时解析）
 *  4. test_support.c 的 C 支撑函数真实引用（非死代码）
 */
#import <Foundation/Foundation.h>
#import <Performance/GSCache.h>
#import <Performance/GSTicker.h>
#include <stdio.h>
#include <string.h>

/* test_support.c 提供：真实被 main() 引用 */
extern int gnustep_perf_test_support_value(void);

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

  /* 1. 类解析 */
  check([GSCache class] != Nil, "GSCache class resolvable");
  check([GSTicker class] != Nil, "GSTicker class resolvable");
  check([NSString class] != Nil, "NSString class resolvable");

  /* 2. GSCache 缓存核心操作 */
  GSCache *cache = [[GSCache alloc] init];
  check(cache != nil, "GSCache alloc+init");
  if (cache != nil) {
    NSString *key = @"k1";
    NSString *val = @"v1";
    [cache setObject: val forKey: key];
    id got = [cache objectForKey: key];
    check([got isEqual: val], "GSCache setObject/objectForKey roundtrip");
    /* objectForKey 对不存在 key 返回 nil（避免依赖 purge 的即时清空语义） */
    check([cache objectForKey: @"__missing__"] == nil,
          "GSCache objectForKey missing key nil");
  }

  /* 3. GSTicker 类运行时加载确认 */
  check(NSClassFromString(@"GSTicker") != Nil,
        "GSTicker class loadable at runtime");

  /* 4. C 支撑函数真实引用 */
  check(gnustep_perf_test_support_value() == 42,
        "test_support C function returns 42");

  [cache release];
  [pool drain];

  if (failures == 0) {
    printf("ALL CHECKS PASSED\n");
    return 0;
  }
  printf("FAILURES: %d\n", failures);
  return 1;
}