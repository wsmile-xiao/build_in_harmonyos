/* test_objfw_c.c — 消费者视角验证 libobjfw1 真实 API roundtrip（纯 C）.
 * libobjfw1 以 --enable-runtime 构建，随包安装 ObjFWRT.h 到
 * include/ObjFWRT/ 子目录（includesubdir=ObjFWRT）；本用例调用 ObjFW
 * runtime 的 objc_allocateClassPair/objc_registerClassPair/objc_getClass
 * 真实 API 并断言结果（避免 R34 空壳测试）。
 * 注：ObjC 框架类（OFString 等）需 -fobjc（OHOS clang 不认），故用
 * 纯 C 可调用的 runtime API 做消费者冒烟。 */
#include <stdio.h>
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
    cls = objc_allocateClassPair((Class)NULL, "OFCTestClass", 0);
    CHECK(cls != NULL);

    /* 2. objc_registerClassPair：注册类对（无返回值，不崩溃即通过） */
    objc_registerClassPair(cls);

    /* 3. objc_getClass：按名查询，验证注册真实生效（返回同一 Class） */
    CHECK(objc_getClass("OFCTestClass") == cls);

    /* 4. 生命周期完整（runtime 管理，正常退出） */
    return 0;
}
