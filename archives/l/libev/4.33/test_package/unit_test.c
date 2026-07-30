#include <ev.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, message)                                                \
  do {                                                                           \
    if (!(condition)) {                                                          \
      fprintf(stderr, "check failed: %s\n", message);                          \
      return 1;                                                                  \
    }                                                                            \
  } while (0)

static int timer_calls = 0;
static int timer_event_error = 0;

static void timer_once_cb(EV_P_ ev_timer *watcher, int revents)
{
  if ((revents & EV_ERROR) != 0 || (revents & EV_TIMER) == 0)
    timer_event_error = 1;
  ++timer_calls;
  ev_timer_stop(EV_A_ watcher);
}

static int test_version(void)
{
  CHECK(ev_version_major() == EV_VERSION_MAJOR, "major version API");
  CHECK(ev_version_minor() == EV_VERSION_MINOR, "minor version API");
  return 0;
}

static int test_loop_userdata(void)
{
  int marker = 42;
  struct ev_loop *loop = ev_loop_new(EVFLAG_AUTO);

  CHECK(loop != NULL, "loop creation");
  CHECK(ev_depth(loop) == 0, "new loop depth");
  ev_set_userdata(loop, &marker);
  CHECK(ev_userdata(loop) == &marker, "loop userdata round trip");
  CHECK(ev_iteration(loop) == 0, "new loop iteration count");
  ev_loop_destroy(loop);
  return 0;
}

static int test_timer_once(void)
{
  struct ev_loop *loop = ev_loop_new(EVFLAG_AUTO);
  ev_timer timer;

  CHECK(loop != NULL, "timer loop creation");
  timer_calls = 0;
  timer_event_error = 0;
  ev_timer_init(&timer, timer_once_cb, 0.0, 0.0);
  ev_timer_start(loop, &timer);
  CHECK(ev_is_active(&timer), "timer active before run");
  ev_run(loop, EVRUN_ONCE);
  CHECK(timer_calls == 1, "timer callback count");
  CHECK(timer_event_error == 0, "timer callback event mask");
  CHECK(!ev_is_active(&timer), "one-shot timer stopped");
  ev_loop_destroy(loop);
  return 0;
}

int main(int argc, char **argv)
{
  if (argc != 2) {
    fprintf(stderr, "usage: %s version|loop_userdata|timer_once\n", argv[0]);
    return 2;
  }
  if (strcmp(argv[1], "version") == 0)
    return test_version();
  if (strcmp(argv[1], "loop_userdata") == 0)
    return test_loop_userdata();
  if (strcmp(argv[1], "timer_once") == 0)
    return test_timer_once();
  fprintf(stderr, "unknown test case: %s\n", argv[1]);
  return 2;
}
