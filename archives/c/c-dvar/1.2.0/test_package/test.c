/* 消费者测试：真实调用 c-dvar API。验证：类型签名解析、变体的序列化/反序列化
 * 往返（struct(string,uint32)）、类型串比较，覆盖大/小端两种字节序。
 * 使用显式返回码检查（conan test_package 以 -DNDEBUG 编译，assert 会被移除）。
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <c-dvar.h>

static int round_trip(int big_endian) {
        CDVarType *type = NULL;
        CDVar *var = NULL;
        void *data = NULL;
        size_t n_data = 0;
        const char *s = NULL;
        uint32_t u = 0;
        int r;

        r = c_dvar_type_new_from_signature(&type, "(su)", 4);
        if (r)
                return 1;

        /* 类型串比较 */
        r = c_dvar_type_compare_string(type, "(su)", 4);
        if (r)
                goto out;

        r = c_dvar_new(&var);
        if (r)
                goto out;

        /* 写入 (string, uint32) 结构体 */
        c_dvar_begin_write(var, big_endian, type, 1);
        r = c_dvar_write(var, "(su)", "hello", UINT32_C(7));
        if (r)
                goto out;
        r = c_dvar_end_write(var, &data, &n_data);
        if (r || !data || !n_data)
                goto out;

        /* 读回并校验 */
        c_dvar_begin_read(var, big_endian, type, 1, data, n_data);
        r = c_dvar_read(var, "(su)", &s, &u);
        if (r)
                goto out;
        if (!s || strcmp(s, "hello") || u != UINT32_C(7))
                goto out;
        r = c_dvar_end_read(var);
        if (r)
                goto out;

        c_dvar_free(var);
        c_dvar_type_free(type);
        free(data);
        return 0;

out:
        if (var)
                c_dvar_free(var);
        if (type)
                c_dvar_type_free(type);
        free(data);
        return 10;
}

int main(void) {
        /* 小端与字节序翻转各做一次往返 */
        if (round_trip(0))
                return 1;
        if (round_trip(1))
                return 2;
        return 0;
}
