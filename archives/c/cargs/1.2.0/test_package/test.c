#include <cargs.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    // 测试 cargs 库的基本功能
    struct cag_option options[] = {
        {.identifier = 'h',
         .access_letters = "h",
         .access_name = "help",
         .value_name = NULL,
         .description = "Shows the help"}
    };

    cag_option_context context;
    cag_option_prepare(&context, options, CAG_ARRAY_SIZE(options), argc, argv);
    
    // 验证 context 已初始化（检查内部状态）
    if (context.option_count != CAG_ARRAY_SIZE(options)) {
        fprintf(stderr, "cag_option_prepare failed: option_count mismatch\n");
        return 1;
    }
    
    printf("test cargs 1.2.0: library linked successfully\n");
    return 0;
}
