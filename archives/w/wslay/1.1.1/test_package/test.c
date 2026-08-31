#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#include <wslay/wslay.h>

struct output_buffer {
  uint8_t data[64];
  size_t length;
};

struct input_buffer {
  const uint8_t *data;
  size_t length;
  size_t offset;
};

static int failures;

#define CHECK(condition) do { \
  if (!(condition)) { \
    fprintf(stderr, "check failed at %s:%d: %s\n", __FILE__, __LINE__, #condition); \
    ++failures; \
  } \
} while (0)

static ssize_t collect_send(const uint8_t *data, size_t length, int flags,
                            void *user_data)
{
  struct output_buffer *output = (struct output_buffer *)user_data;
  (void)flags;
  if (length > sizeof(output->data) - output->length) {
    return -1;
  }
  memcpy(output->data + output->length, data, length);
  output->length += length;
  return (ssize_t)length;
}

static ssize_t feed_recv(uint8_t *data, size_t length, int flags,
                         void *user_data)
{
  struct input_buffer *input = (struct input_buffer *)user_data;
  size_t remaining;
  size_t amount;
  (void)flags;
  if (input->offset >= input->length) {
    return -1;
  }
  remaining = input->length - input->offset;
  amount = remaining < length ? remaining : length;
  memcpy(data, input->data + input->offset, amount);
  input->offset += amount;
  return (ssize_t)amount;
}

static int fixed_mask(uint8_t *mask, size_t length, void *user_data)
{
  static const uint8_t key[] = {0x37u, 0xfau, 0x21u, 0x3du};
  (void)user_data;
  if (length != sizeof(key)) {
    return -1;
  }
  memcpy(mask, key, sizeof(key));
  return 0;
}

static void round_trip(uint8_t masked)
{
  static const uint8_t payload[] = {'h', 'e', 'l', 'l', 'o'};
  uint8_t recv_buf[sizeof(payload)];
  static const uint8_t unmasked_frame[] = {
    0x81u, 0x05u, 'h', 'e', 'l', 'l', 'o'
  };
  static const uint8_t masked_frame[] = {
    0x81u, 0x85u, 0x37u, 0xfau, 0x21u, 0x3du,
    0x5fu, 0x9fu, 0x4du, 0x51u, 0x58u
  };
  const uint8_t *expected = masked ? masked_frame : unmasked_frame;
  size_t expected_length = masked ? sizeof(masked_frame) : sizeof(unmasked_frame);
  struct output_buffer output = {{0}, 0};
  struct wslay_frame_callbacks send_callbacks = {
    collect_send, NULL, fixed_mask
  };
  struct wslay_frame_context *sender = NULL;
  struct wslay_frame_iocb send_iocb = {
    1, WSLAY_RSV_NONE, WSLAY_TEXT_FRAME, sizeof(payload), masked,
    payload, sizeof(payload)
  };
  struct input_buffer input;
  struct wslay_frame_callbacks recv_callbacks = {NULL, feed_recv, NULL};
  struct wslay_frame_context *receiver = NULL;
  struct wslay_frame_iocb recv_iocb;
  ssize_t sent;
  ssize_t received;

  CHECK(wslay_frame_context_init(&sender, &send_callbacks, &output) == 0);
  if (sender == NULL) {
    return;
  }
  sent = wslay_frame_send(sender, &send_iocb);
  CHECK(sent == (ssize_t)sizeof(payload));
  CHECK(output.length == expected_length);
  CHECK(memcmp(output.data, expected, expected_length) == 0);
  wslay_frame_context_free(sender);

  input.data = output.data;
  input.length = output.length;
  input.offset = 0;
  CHECK(wslay_frame_context_init(&receiver, &recv_callbacks, &input) == 0);
  if (receiver == NULL) {
    return;
  }
  memset(&recv_iocb, 0, sizeof(recv_iocb));
  recv_iocb.data = recv_buf;
  recv_iocb.data_length = sizeof(recv_buf);
  received = wslay_frame_recv(receiver, &recv_iocb);
  CHECK(received == (ssize_t)sizeof(payload));
  CHECK(recv_iocb.fin == 1);
  CHECK(recv_iocb.opcode == WSLAY_TEXT_FRAME);
  CHECK(recv_iocb.mask == masked);
  CHECK(recv_iocb.payload_length == sizeof(payload));
  CHECK(recv_iocb.data_length == sizeof(payload));
  CHECK(memcmp(recv_iocb.data, payload, sizeof(payload)) == 0);
  CHECK(input.offset == input.length);
  wslay_frame_context_free(receiver);
}

int main(void)
{
  round_trip(0);
  round_trip(1);
  if (failures != 0) {
    fprintf(stderr, "%d wslay API checks failed\n", failures);
    return EXIT_FAILURE;
  }
  puts("wslay frame send/receive checks passed");
  return EXIT_SUCCESS;
}
