/* 真实断言：把 ECL（Embeddable Common-Lisp）当运行时嵌进来，
 * 求值几个结果可手算的 Lisp 表达式并比对返回值。
 *
 * 为什么不能只 dlopen：ECL 的价值在于「能真的跑起一个 Lisp 运行时并求值」。
 * 库能加载、cl_boot 符号存在，都不能说明 bootstrap 起得来——
 * ECL 启动时要初始化 GC、读入内建包与符号表，任何一环在鸿蒙上不成立，
 * dlopen 照样成功而 cl_boot 直接崩。故必须链接后真正 boot 并求值。 */
#include <stdio.h>
#include <ecl/ecl.h>

int main(int argc, char **argv) {
    cl_boot(argc, argv);                       /* 起 Lisp 运行时（GC + 内建包 + 读取器） */

    /* ① 整数算术：(* (+ 1 2) 7) = 21 */
    cl_object r1 = cl_eval(c_string_to_object("(* (+ 1 2) 7)"));
    if (!ECL_FIXNUMP(r1) || ecl_fixnum(r1) != 21) {
        fprintf(stderr, "(* (+ 1 2) 7) 应为 21\n"); return 1;
    }

    /* ② bignum：ECL 内建大整数（走 GMP），(expt 2 100) 的十进制位数为 31 */
    cl_object r2 = cl_eval(c_string_to_object(
        "(length (format nil \"~D\" (expt 2 100)))"));
    if (!ECL_FIXNUMP(r2) || ecl_fixnum(r2) != 31) {
        fprintf(stderr, "(expt 2 100) 的十进制位数应为 31\n"); return 1;
    }

    /* ③ 闭包与 funcall：真正走一遍编译/求值器与调用约定 */
    cl_object fn = cl_eval(c_string_to_object("(lambda (x) (* x x))"));
    cl_object r3 = cl_funcall(2, fn, ecl_make_fixnum(12));
    if (!ECL_FIXNUMP(r3) || ecl_fixnum(r3) != 144) {
        fprintf(stderr, "((lambda (x) (* x x)) 12) 应为 144\n"); return 1;
    }

    /* ④ 列表处理：(reduce #'+ '(1 2 3 4 5)) = 15 */
    cl_object r4 = cl_eval(c_string_to_object("(reduce #'+ (list 1 2 3 4 5))"));
    if (!ECL_FIXNUMP(r4) || ecl_fixnum(r4) != 15) {
        fprintf(stderr, "(reduce #'+ '(1 2 3 4 5)) 应为 15\n"); return 1;
    }

    printf("ecl: (*(+ 1 2)7)=21 通过；(expt 2 100) 位数=31 通过；"
           "闭包 funcall=144 通过；reduce=15 通过\n");
    cl_shutdown();
    return 0;
}
