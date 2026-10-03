/*
 * Consumer smoke test for the packaged tgl library.
 *
 * It drives the public API the way a downstream application does: initialize
 * a tgl_state, register the application id, build and compare peer ids,
 * insert peers into the peer tree, walk it back, and check the allocator
 * accounting before tearing the state down again.  Nothing here touches the
 * network, so the test also runs on an offline device.
 */
#include <stdio.h>
#include <string.h>

#include <tgl/tgl.h>

static int checks;
static int failed;

static void check(int condition, const char *what)
{
  checks++;
  if (condition) {
    printf("ok %d - %s\n", checks, what);
  } else {
    failed++;
    printf("FAIL %d - %s\n", checks, what);
  }
}

static void count_peer(tgl_peer_t *P, void *extra)
{
  (void)P;
  (*(int *)extra)++;
}

int main(void)
{
  struct tgl_state *TLS;
  tgl_peer_id_t user, chat, same_user, other_user;
  int peers = 0;
  long long allocated;

  check(strcmp(TGL_VERSION, "2.1.0") == 0,
        "TGL_VERSION is exported by the public header");

  TLS = tgl_state_alloc();
  check(TLS != NULL, "tgl_state_alloc() returns a usable state");

  tgl_set_verbosity(TLS, 0);
  tgl_incr_verbosity(TLS);
  tgl_register_app_id(TLS, 12345, "0123456789abcdef0123456789abcdef");
  tgl_set_app_version(TLS, "tgl-consumer-test");
  tgl_disable_link_preview(TLS);

  user = TGL_MK_USER(4242);
  same_user = TGL_MK_USER(4242);
  other_user = TGL_MK_USER(4243);
  chat = TGL_MK_CHAT(777);

  check(tgl_get_peer_type(user) == TGL_PEER_USER,
        "TGL_MK_USER() sets the user peer type");
  check(tgl_get_peer_id(user) == 4242, "TGL_MK_USER() keeps the peer id");
  check(tgl_get_peer_type(chat) == TGL_PEER_CHAT,
        "TGL_MK_CHAT() sets the chat peer type");
  check(tgl_cmp_peer_id(user, same_user) == 0,
        "tgl_cmp_peer_id() matches equal peer ids");
  check(tgl_cmp_peer_id(user, other_user) != 0,
        "tgl_cmp_peer_id() separates different peer ids");

  tgl_insert_empty_user(TLS, 4242);
  tgl_insert_empty_chat(TLS, 777);
  check(tgl_peer_get(TLS, user) != NULL,
        "tgl_peer_get() finds the inserted user");
  check(tgl_peer_get(TLS, chat) != NULL,
        "tgl_peer_get() finds the inserted chat");
  check(tgl_peer_get(TLS, other_user) == NULL,
        "tgl_peer_get() reports a peer that was never inserted");

  tgl_peer_iterator_ex(TLS, count_peer, &peers);
  check(peers >= 2, "tgl_peer_iterator_ex() visits the inserted peers");

  allocated = tgl_get_allocated_bytes();
  check(allocated > 0, "tgl_get_allocated_bytes() reports tracked allocations");

  tgl_free_all(TLS);

  printf("%d checks, %d failures\n", checks, failed);
  return failed == 0 ? 0 : 1;
}
