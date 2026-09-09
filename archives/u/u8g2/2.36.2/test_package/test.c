#include <stdio.h>
#include "u8g2/u8g2.h"

int main(void) {
    u8g2_t u8g2;

    /* 实质调用 u8g2 API：初始化一个无硬件（null）显示器实例，
       完成清屏→绘制→发送缓冲区全流程，验证库可链接且逻辑正常 */
    u8g2_Setup_null(&u8g2, U8G2_R0, u8x8_byte_empty, u8x8_dummy_cb);
    u8g2_InitDisplay(&u8g2);
    u8g2_SetPowerSave(&u8g2, 0);
    u8g2_ClearBuffer(&u8g2);
    u8g2_SetFont(&u8g2, u8g2_font_5x8_tr);
    u8g2_DrawStr(&u8g2, 0, 8, "u8g2 ok");
    u8g2_SendBuffer(&u8g2);

    /* 帧循环（FirstPage/NextPage）走一遍，确保页面回调链正常 */
    u8g2_FirstPage(&u8g2);
    do {
        u8g2_DrawBox(&u8g2, 0, 0, 4, 4);
    } while (u8g2_NextPage(&u8g2));

    printf("test u8g2 2.36.2: OK\n");
    return 0;
}
