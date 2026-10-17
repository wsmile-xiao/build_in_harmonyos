/*
 * test_libsbp.c — libsbp/6.5.1 消费者冒烟测试（纯 C）
 *
 * 实质调用被测包公开 API（R34）：
 *  1. CRC16（edc.c crc16_ccitt）已知向量 + 累进校验
 *  2. 消息编解码往返：sbp_message_encode / sbp_message_decode（heartbeat）
 *  3. 帧循环：sbp_message_send 构造完整 SBP 帧（preamble/header/payload/crc）
 *     + sbp_process 状态机逐状态还原消息
 */
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include <libsbp/edc.h>
#include <libsbp/sbp.h>
#include <libsbp/sbp_msg.h>

static u8 frame_buf[SBP_MAX_FRAME_LEN];
static u32 frame_len = 0;

static s32 mem_write(u8 *buff, u32 n, void *context)
{
    (void)context;
    memcpy(frame_buf + frame_len, buff, n);
    frame_len += n;
    return (s32)n;
}

static s32 mem_read(u8 *buff, u32 n, void *context)
{
    u32 *pos = (u32 *)context;
    u32 remain = frame_len - *pos;
    u32 to_read = (n < remain) ? n : remain;
    memcpy(buff, frame_buf + *pos, to_read);
    *pos += to_read;
    return (s32)to_read;
}

static void test_crc16(void)
{
    /* SBP CRC-16-CCITT (X.25 变体，初始值 0)："123456789" -> 0x906E */
    const u8 data[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    u16 crc = crc16_ccitt(data, sizeof(data), 0);
    assert(crc == 0x906E);
    /* 累进计算与一次性计算一致 */
    u16 acc = crc16_ccitt(data, 4, 0);
    acc = crc16_ccitt(data + 4, 5, acc);
    assert(acc == crc);
    printf("PASS: crc16_ccitt known vector 0x%04X + streaming\n", crc);
}

static void test_message_encode_decode(void)
{
    u8 buf[SBP_MAX_FRAME_LEN];
    uint8_t n_written = 0;
    uint8_t n_read = 0;
    sbp_msg_t msg_out, msg_in;
    s8 rc;

    memset(&msg_out, 0, sizeof(msg_out));
    memset(&msg_in, 0, sizeof(msg_in));
    msg_out.heartbeat.flags = 0x000000C5u;

    rc = sbp_message_encode(buf, (uint8_t)sizeof(buf), &n_written,
                            SbpMsgHeartbeat, &msg_out);
    assert(rc == SBP_OK);
    assert(n_written == SBP_MSG_HEARTBEAT_ENCODED_LEN);

    rc = sbp_message_decode(buf, n_written, &n_read, SbpMsgHeartbeat, &msg_in);
    assert(rc == SBP_OK);
    assert(n_read == n_written);
    assert(msg_in.heartbeat.flags == 0x000000C5u);
    printf("PASS: heartbeat message encode/decode roundtrip (flags=0x%X)\n",
           (unsigned)msg_in.heartbeat.flags);
}

static u16 cb_sender_id = 0;
static sbp_msg_type_t cb_msg_type = SbpMsgAll;
static u32 cb_flags = 0;
static int cb_called = 0;

static void heartbeat_cb(u16 sender_id, sbp_msg_type_t msg_type,
                         const sbp_msg_t *msg, void *context)
{
    (void)context;
    cb_sender_id = sender_id;
    cb_msg_type = msg_type;
    cb_flags = msg->heartbeat.flags;
    cb_called++;
}

static void test_frame_send_process(void)
{
    sbp_state_t state;
    sbp_msg_t msg;
    sbp_msg_callbacks_node_t cb_node;
    u32 pos = 0;
    s8 rc = SBP_OK;

    memset(&msg, 0, sizeof(msg));
    msg.heartbeat.flags = 0xA5A55A5Au;

    sbp_state_init(&state);
    frame_len = 0;
    rc = sbp_message_send(&state, SbpMsgHeartbeat, 0x2042, &msg, mem_write);
    assert(rc == SBP_OK);
    /* preamble(1)+type(2)+sender(2)+len(1)+payload(4)+crc(2) = 12 */
    assert(frame_len == SBP_HEADER_LEN + SBP_MSG_HEARTBEAT_ENCODED_LEN + SBP_CRC_LEN);

    /* 完整帧逐字节校验 */
    assert(frame_buf[SBP_FRAME_OFFSET_PREAMBLE] == SBP_PREAMBLE);
    u16 msg_type = (u16)frame_buf[SBP_FRAME_OFFSET_MSGTYPE] |
                   ((u16)frame_buf[SBP_FRAME_OFFSET_MSGTYPE + 1] << 8);
    assert(msg_type == (u16)SbpMsgHeartbeat);
    u16 sender = (u16)frame_buf[SBP_FRAME_OFFSET_SENDERID] |
                 ((u16)frame_buf[SBP_FRAME_OFFSET_SENDERID + 1] << 8);
    assert(sender == 0x2042);

    /* 状态机从帧缓冲还原消息：注册 heartbeat 回调接收解码后的结构体 */
    sbp_state_init(&state);
    sbp_state_set_io_context(&state, &pos);
    rc = sbp_callback_register(&state, SbpMsgHeartbeat, heartbeat_cb, NULL, &cb_node);
    assert(rc == SBP_OK);
    for (;;) {
        rc = sbp_process(&state, mem_read);
        if (rc != SBP_OK) {
            break; /* SBP_OK_CALLBACK_EXECUTED / 负值错误 */
        }
    }
    assert(rc == SBP_OK_CALLBACK_EXECUTED);
    assert(cb_called == 1);
    assert(cb_sender_id == 0x2042);
    assert(cb_msg_type == SbpMsgHeartbeat);
    assert(cb_flags == 0xA5A55A5Au);
    printf("PASS: frame send/process roundtrip (sender=0x%04X flags=0x%08X)\n",
           cb_sender_id, cb_flags);
}

int main(void)
{
    printf("== libsbp 6.5.1 consumer smoke test ==\n");
    test_crc16();
    test_message_encode_decode();
    test_frame_send_process();
    printf("ALL TESTS PASSED\n");
    return 0;
}
