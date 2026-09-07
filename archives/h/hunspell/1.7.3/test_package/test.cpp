/* test_package/test.cpp — hunspell 1.7.3 消费者视角 smoke（R34）。

 * 用 libhunspell-1.7 加载内置迷你词典 test.aff + test.dic，真实执行
 * spell()：命中 "hello"/"world" 应返回 true，未命中 "helo" 应返回 false。
 */
#include <hunspell/hunspell.hxx>

#include <cstdio>
#include <cstring>

int main() {
    Hunspell *sp = new Hunspell("test.aff", "test.dic");
    if (sp == NULL) {
        fprintf(stderr, "FAIL: Hunspell(test.aff, test.dic) constructor returned NULL\n");
        return 1;
    }
    if (!sp->spell("hello")) {
        fprintf(stderr, "FAIL: 'hello' should be in dictionary\n");
        return 1;
    }
    if (!sp->spell("world")) {
        fprintf(stderr, "FAIL: 'world' should be in dictionary\n");
        return 1;
    }
    if (sp->spell("helo")) {
        fprintf(stderr, "FAIL: 'helo' should NOT be in dictionary\n");
        return 1;
    }
    delete sp;
    printf("hunspell consumer test: OK\n");
    return 0;
}
