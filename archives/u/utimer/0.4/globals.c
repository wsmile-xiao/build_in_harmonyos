#include "src/utimer.h"

GMainLoop *loop;
gboolean paused;
struct termios savedttystate;
Config ut_config;
