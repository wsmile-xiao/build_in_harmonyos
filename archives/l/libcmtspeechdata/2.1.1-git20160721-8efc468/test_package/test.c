#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <cmtspeech.h>

int main(void)
{
    cmtspeech_cmd_t cmd;
    memset(&cmd, 0xa5, sizeof(cmd));
    if (cmtspeech_msg_encode_reset_conn_req(&cmd) != CMTSPEECH_CTRL_LEN)
        return 1;
    if (cmtspeech_msg_get_type(cmd) != CMTSPEECH_RESET_CONN_REQ ||
        cmtspeech_msg_get_domain(cmd) != CMTSPEECH_DOMAIN_CONTROL)
        return 2;
    if (cmd.d.buf[0] != 0 || cmd.d.buf[1] != 0 ||
        cmd.d.buf[2] != 0 || cmd.d.buf[3] != 0x01)
        return 3;
    puts("libcmtspeechdata installed API test passed");
    return 0;
}
