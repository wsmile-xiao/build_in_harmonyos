#include <stdio.h>
#include <string.h>

#include "microui.h"

static int text_width(mu_Font font, const char *text, int len)
{
    (void)font;
    (void)text;
    return len * 8;
}

static int text_height(mu_Font font)
{
    (void)font;
    return 16;
}

int main(void)
{
    mu_Context ctx;
    mu_Command *command = NULL;
    int command_count = 0;

    mu_init(&ctx);
    if (ctx.style == NULL || ctx.style->padding != 5) {
        return 1;
    }
    ctx.text_width = text_width;
    ctx.text_height = text_height;

    mu_begin(&ctx);
    if (!mu_begin_window(&ctx, "test", mu_rect(0, 0, 160, 100))) {
        return 2;
    }
    mu_layout_row(&ctx, 1, (int[]){-1}, 24);
    mu_label(&ctx, "microui");
    mu_end_window(&ctx);
    mu_end(&ctx);

    while (mu_next_command(&ctx, &command)) {
        if (command == NULL || command->type <= 0) {
            return 3;
        }
        command_count++;
    }
    if (command_count == 0 || strcmp(MU_VERSION, "2.02") != 0) {
        return 4;
    }

    printf("microui API test passed: %d commands\n", command_count);
    return 0;
}
