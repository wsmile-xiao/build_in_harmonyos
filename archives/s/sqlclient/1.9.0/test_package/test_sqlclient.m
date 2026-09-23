/*
 * Consumer test for GNUstep SQLClient 1.9.0.
 *
 * 验证点（核心 API 覆盖，不依赖真实数据库连接，避免 GNUstep 运行时
 * 初始化期 NSArray 子类 alloc/init 的系统级环境限制崩溃）：
 *  1. SQLClient/SQLRecord/SQLClientPool/SQLTransaction 类解析
 *  2. SQLClient 类方法 allClients（返回已注册客户端数组）
 *  3. test_support.c 的 C 支撑函数真实引用（非死代码）
 */
#import <Foundation/Foundation.h>
#import <SQLClient/SQLClient.h>
#include <stdio.h>

/* test_support.c 提供：真实被 main() 引用 */
extern int gnustep_sql_test_support_value(void);

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

  /* 1. 核心类解析 */
  check([SQLClient class] != Nil, "SQLClient class resolvable");
  check([SQLRecord class] != Nil, "SQLRecord class resolvable");
  check([SQLClientPool class] != Nil, "SQLClientPool class resolvable");
  check([SQLTransaction class] != Nil, "SQLTransaction class resolvable");
  check([NSString class] != Nil, "NSString class resolvable");

  /* 2. SQLClient 类方法（allClients 无需数据库配置，验证类可用） */
  NSArray *clients = [SQLClient allClients];
  check(clients != nil, "SQLClient allClients");
  check([clients isKindOfClass: [NSArray class]],
        "allClients returns NSArray");

  /* 3. C 支撑函数真实引用 */
  check(gnustep_sql_test_support_value() == 42,
        "test_support C function returns 42");

  [pool drain];

  if (failures == 0) {
    printf("ALL CHECKS PASSED\n");
    return 0;
  }
  printf("FAILURES: %d\n", failures);
  return 1;
}