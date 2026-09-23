// ccScript 消费者测试：以库使用者身份真实调用公开 API——
// 编译一个内联脚本并检查编译错误数（编译 / 链接 / 运行 / 退出码判定）
#include <ccscript.h>

#include <cstdio>
#include <cstring>

using namespace ucommon;

int main() {
    Script::init();

    const char *path = "smoke_ccscript.scr";
    FILE *fp = fopen(path, "w");
    if (!fp) {
        printf("FAIL: cannot create script file\n");
        return 1;
    }
    // 最小合法脚本（语法参照上游 test/testscript.scr 的 @main 段）
    fputs("@main\n\tnop\n\texit\n", fp);
    fclose(fp);

    Script *image = Script::compile(NULL, path);
    if (!image) {
        remove(path);
        printf("FAIL: Script::compile returned null\n");
        return 1;
    }
    const unsigned errors = image->getErrors();
    delete image;
    remove(path);

    if (errors) {
        printf("FAIL: script compile reported %u error(s)\n", errors);
        return 1;
    }
    printf("ccscript Script::compile OK\n");
    return 0;
}
