/* 消费者测试：真实调用 c-utf8 API。验证：c_utf8_verify_ascii()/c_utf8_verify()
 * 对纯 ASCII、合法多字节 UTF-8、非法序列与 ASCII 边界的推进/剩余语义。
 */
#include <assert.h>
#include <stddef.h>
#include <c-utf8.h>

int main(void) {
        /* 1) 纯 ASCII：verify_ascii 与 verify 均应完整消费到 NUL、剩余 0 */
        const char *p = "hello";
        size_t len = 5;
        c_utf8_verify_ascii(&p, &len);
        assert(*p == '\0' && len == 0);

        p = "hello";
        len = 5;
        c_utf8_verify(&p, &len);
        assert(*p == '\0' && len == 0);

        /* 2) 合法多字节 UTF-8（U+00E4 = C3 A4）：verify 完整消费 */
        const char utf8[] = {'a', (char)0xc3, (char)0xa4, 'b', '\0'};
        p = utf8;
        len = 4;
        c_utf8_verify(&p, &len);
        assert(*p == '\0' && len == 0);

        /* 3) verify_ascii 遇非 ASCII 停止：指针停在 0xc3、剩余 3 字节 */
        p = utf8;
        len = 4;
        c_utf8_verify_ascii(&p, &len);
        assert(p == utf8 + 1 && len == 3);

        /* 4) 非法序列 0xff：verify 停在非法字节，消费 'a' 后剩余 2 字节 */
        const char bad[] = {'a', (char)0xff, 'b', '\0'};
        p = bad;
        len = 3;
        c_utf8_verify(&p, &len);
        assert(p == bad + 1 && len == 2);

        /* 5) 截断的多字节序列（续字节缺失）：verify 停在序列首字节 */
        const char trunc[] = {(char)0xc3, 'a', '\0'};
        p = trunc;
        len = 2;
        c_utf8_verify(&p, &len);
        assert(p == trunc && len == 2);

        return 0;
}
