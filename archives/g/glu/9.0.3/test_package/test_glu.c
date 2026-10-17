/**
 * glu 9.0.3 test_package —— 消费者视角的编译 + 链接 + **真实执行**验证。
 *
 * 断言只依赖不需要 GL 上下文的 API（可在无显示服务的环境运行）：
 *   ① gluErrorString() 对合法错误码返回非空描述（纯查表函数）；
 *   ② gluErrorString() 对 NURBS 错误区间（GLU_NURBS_ERROR1..）同样返回非空；
 *   ③ GLU 版本宏为 1.3（GLU_VERSION == 100800）。
 *
 * ③ 之外的关键点：本文件**直接调用 gluErrorString**，因此若库未导出 glu* 符号
 * （即补丁 0001 未生效、gnu_symbol_visibility:hidden 仍在该场景下生效），
 * 链接阶段就会失败（undefined reference to `gluErrorString`）——这正是该补丁的回归测试。
 */
#include <stdio.h>
#include <string.h>

#include <GL/glu.h>

static int failures = 0;

static void check(int cond, const char *what)
{
    printf("  %s %s\n", cond ? "OK:" : "FAIL:", what);
    if (!cond)
        failures++;
}

int main(void)
{
    printf("glu smoke test\n");

    /* ① 合法错误码 → 非空描述（GLU_enum 区间的第一个） */
    const GLubyte *e_enum = gluErrorString(GLU_INVALID_ENUM);
    check(e_enum != NULL && e_enum[0] != '\0',
          "gluErrorString(GLU_INVALID_ENUM) returns a non-empty string");
    printf("    GLU_INVALID_ENUM   -> \"%s\"\n", e_enum ? (const char *)e_enum : "(null)");

    /* ② NURBS 错误区间（走 __gluNURBSErrorString 分支，验证符号解析正确） */
    const GLubyte *e_nurbs = gluErrorString(GLU_NURBS_ERROR1);
    check(e_nurbs != NULL && e_nurbs[0] != '\0',
          "gluErrorString(GLU_NURBS_ERROR1) returns a non-empty string");
    printf("    GLU_NURBS_ERROR1   -> \"%s\"\n", e_nurbs ? (const char *)e_nurbs : "(null)");

    /* ③ 版本宏 */
    printf("    GLU_VERSION        = %d\n", GLU_VERSION);
    check(GLU_VERSION == 100800, "GLU_VERSION == 100800 (i.e. 1.3)");

    if (failures) {
        printf("glu smoke test: FAILED (%d assertion(s))\n", failures);
        return 1;
    }
    printf("glu smoke test: PASS\n");
    return 0;
}
