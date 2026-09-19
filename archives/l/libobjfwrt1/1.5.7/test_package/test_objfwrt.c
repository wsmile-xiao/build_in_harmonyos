/* test_objfwrt.c — 消费者视角验证 libobjfwrt1（ObjFW runtime）公开 API：
 * objc_allocateClassPair / objc_registerClassPair / objc_getClass 真实
 * roundtrip（无网络依赖，仅验证库可被第三方编译/链接/调用）。
 * 注：ObjFW runtime 无 objc_disposeClassPair，注册后由 runtime 管理；
 * OHOS 无系统 objc/objc.h，ObjFWRT.h 自带类型定义。 */
#include <stdio.h>

/* 通过 ObjFWRT.h 提供 objc_* 运行时 API 与类型定义
 * （ObjFW 安装 ObjFWRT.h 到 include/ObjFWRT/ 子目录，includesubdir=ObjFWRT） */
#include <ObjFWRT/ObjFWRT.h>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void)
{
    Class cls;

    /* 1. objc_allocateClassPair：分配新类对（可失败，断言非 NULL） */
    cls = objc_allocateClassPair((Class)NULL, "OFTestClass", 0);
    CHECK(cls != NULL);

    /* 2. objc_registerClassPair：注册类对 */
    objc_registerClassPair(cls);

    /* 3. objc_getClass：按名查询，验证注册真实生效（可失败，断言非 NULL） */
    CHECK(objc_getClass("OFTestClass") == cls);

    /* 4. 生命周期完整（runtime 管理类生命周期，不崩溃） */
    printf("test_objfwrt: OK (ObjFW runtime class roundtrip)\n");
    return 0;
}
