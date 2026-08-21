/* Auto-generated stub implementations matching real systemd 261 sd-event.h */
#include <stdint.h>
#include <sys/types.h>
#include <stddef.h>
#include "systemd/sd-event.h"

int sd_event_default(sd_event **ret) {
    (void) ret;
    return 0;
}
int sd_event_new(sd_event **ret) {
    (void) ret;
    return 0;
}
int sd_event_add_io(sd_event *e, sd_event_source **ret, int fd, uint32_t events, sd_event_io_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) fd; (void) events; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_time(sd_event *e, sd_event_source **ret, clockid_t clock, uint64_t usec, uint64_t accuracy, sd_event_time_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) clock; (void) usec; (void) accuracy; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_time_relative(sd_event *e, sd_event_source **ret, clockid_t clock, uint64_t usec, uint64_t accuracy, sd_event_time_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) clock; (void) usec; (void) accuracy; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_signal(sd_event *e, sd_event_source **ret, int sig, sd_event_signal_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) sig; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_child(sd_event *e, sd_event_source **ret, pid_t pid, int options, sd_event_child_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) pid; (void) options; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_child_pidfd(sd_event *e, sd_event_source **ret, int pidfd, int options, sd_event_child_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) pidfd; (void) options; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_inotify(sd_event *e, sd_event_source **ret, const char *path, uint32_t mask, sd_event_inotify_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) path; (void) mask; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_inotify_fd(sd_event *e, sd_event_source **ret, int fd, uint32_t mask, sd_event_inotify_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) fd; (void) mask; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_defer(sd_event *e, sd_event_source **ret, sd_event_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_post(sd_event *e, sd_event_source **ret, sd_event_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_exit(sd_event *e, sd_event_source **ret, sd_event_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_memory_pressure(sd_event *e, sd_event_source **ret, sd_event_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_cpu_pressure(sd_event *e, sd_event_source **ret, sd_event_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) callback; (void) userdata;
    return 0;
}
int sd_event_add_io_pressure(sd_event *e, sd_event_source **ret, sd_event_handler_t callback, void *userdata) {
    (void) e; (void) ret; (void) callback; (void) userdata;
    return 0;
}
int sd_event_prepare(sd_event *e) {
    (void) e;
    return 0;
}
int sd_event_wait(sd_event *e, uint64_t timeout) {
    (void) e; (void) timeout;
    return 0;
}
int sd_event_dispatch(sd_event *e) {
    (void) e;
    return 0;
}
int sd_event_run(sd_event *e, uint64_t timeout) {
    (void) e; (void) timeout;
    return 0;
}
int sd_event_loop(sd_event *e) {
    (void) e;
    return 0;
}
int sd_event_exit(sd_event *e, int code) {
    (void) e; (void) code;
    return 0;
}
int sd_event_now(sd_event *e, clockid_t clock, uint64_t *ret) {
    (void) e; (void) clock; (void) ret;
    return 0;
}
int sd_event_get_fd(sd_event *e) {
    (void) e;
    return 0;
}
int sd_event_get_state(sd_event *e) {
    (void) e;
    return 0;
}
int sd_event_get_tid(sd_event *e, pid_t *ret) {
    (void) e; (void) ret;
    return 0;
}
int sd_event_get_exit_code(sd_event *e, int *ret) {
    (void) e; (void) ret;
    return 0;
}
int sd_event_set_watchdog(sd_event *e, int b) {
    (void) e; (void) b;
    return 0;
}
int sd_event_get_watchdog(sd_event *e) {
    (void) e;
    return 0;
}
int sd_event_get_iteration(sd_event *e, uint64_t *ret) {
    (void) e; (void) ret;
    return 0;
}
int sd_event_set_signal_exit(sd_event *e, int b) {
    (void) e; (void) b;
    return 0;
}
int sd_event_set_exit_on_idle(sd_event *e, int b) {
    (void) e; (void) b;
    return 0;
}
int sd_event_get_exit_on_idle(sd_event *e) {
    (void) e;
    return 0;
}
int sd_event_source_set_description(sd_event_source *s, const char *description) {
    (void) s; (void) description;
    return 0;
}
int sd_event_source_get_description(sd_event_source *s, const char **ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_set_prepare(sd_event_source *s, sd_event_handler_t callback) {
    (void) s; (void) callback;
    return 0;
}
int sd_event_source_get_pending(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_get_priority(sd_event_source *s, int64_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_set_priority(sd_event_source *s, int64_t priority) {
    (void) s; (void) priority;
    return 0;
}
int sd_event_source_get_enabled(sd_event_source *s, int *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_set_enabled(sd_event_source *s, int enabled) {
    (void) s; (void) enabled;
    return 0;
}
int sd_event_source_get_io_fd(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_set_io_fd(sd_event_source *s, int fd) {
    (void) s; (void) fd;
    return 0;
}
int sd_event_source_get_io_fd_own(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_set_io_fd_own(sd_event_source *s, int own) {
    (void) s; (void) own;
    return 0;
}
int sd_event_source_get_io_events(sd_event_source *s, uint32_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_set_io_events(sd_event_source *s, uint32_t events) {
    (void) s; (void) events;
    return 0;
}
int sd_event_source_get_io_revents(sd_event_source *s, uint32_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_get_time(sd_event_source *s, uint64_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_set_time(sd_event_source *s, uint64_t usec) {
    (void) s; (void) usec;
    return 0;
}
int sd_event_source_set_time_relative(sd_event_source *s, uint64_t usec) {
    (void) s; (void) usec;
    return 0;
}
int sd_event_source_get_time_accuracy(sd_event_source *s, uint64_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_set_time_accuracy(sd_event_source *s, uint64_t usec) {
    (void) s; (void) usec;
    return 0;
}
int sd_event_source_get_time_clock(sd_event_source *s, clockid_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_get_signal(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_get_child_pid(sd_event_source *s, pid_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_get_child_pidfd(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_get_child_pidfd_own(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_set_child_pidfd_own(sd_event_source *s, int own) {
    (void) s; (void) own;
    return 0;
}
int sd_event_source_get_child_process_own(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_set_child_process_own(sd_event_source *s, int own) {
    (void) s; (void) own;
    return 0;
}
int sd_event_source_send_child_signal(sd_event_source *s, int sig, const siginfo_t *si, unsigned flags) {
    (void) s; (void) sig; (void) si; (void) flags;
    return 0;
}
int sd_event_source_get_inotify_mask(sd_event_source *s, uint32_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_get_inotify_path(sd_event_source *s, const char **ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_set_memory_pressure_type(sd_event_source *s, const char *ty) {
    (void) s; (void) ty;
    return 0;
}
int sd_event_source_set_memory_pressure_period(sd_event_source *s, uint64_t threshold_usec, uint64_t window_usec) {
    (void) s; (void) threshold_usec; (void) window_usec;
    return 0;
}
int sd_event_source_set_cpu_pressure_type(sd_event_source *s, const char *ty) {
    (void) s; (void) ty;
    return 0;
}
int sd_event_source_set_cpu_pressure_period(sd_event_source *s, uint64_t threshold_usec, uint64_t window_usec) {
    (void) s; (void) threshold_usec; (void) window_usec;
    return 0;
}
int sd_event_source_set_io_pressure_type(sd_event_source *s, const char *ty) {
    (void) s; (void) ty;
    return 0;
}
int sd_event_source_set_io_pressure_period(sd_event_source *s, uint64_t threshold_usec, uint64_t window_usec) {
    (void) s; (void) threshold_usec; (void) window_usec;
    return 0;
}
int sd_event_source_set_destroy_callback(sd_event_source *s, sd_event_destroy_t callback) {
    (void) s; (void) callback;
    return 0;
}
int sd_event_source_get_destroy_callback(sd_event_source *s, sd_event_destroy_t *ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_event_source_get_floating(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_set_floating(sd_event_source *s, int b) {
    (void) s; (void) b;
    return 0;
}
int sd_event_source_get_exit_on_failure(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_set_exit_on_failure(sd_event_source *s, int b) {
    (void) s; (void) b;
    return 0;
}
int sd_event_source_set_ratelimit(sd_event_source *s, uint64_t interval_usec, unsigned burst) {
    (void) s; (void) interval_usec; (void) burst;
    return 0;
}
int sd_event_source_get_ratelimit(sd_event_source *s, uint64_t *ret_interval_usec, unsigned *ret_burst) {
    (void) s; (void) ret_interval_usec; (void) ret_burst;
    return 0;
}
int sd_event_source_is_ratelimited(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_source_set_ratelimit_expire_callback(sd_event_source *s, sd_event_handler_t callback) {
    (void) s; (void) callback;
    return 0;
}
int sd_event_source_leave_ratelimit(sd_event_source *s) {
    (void) s;
    return 0;
}
int sd_event_trim_memory(void) {

    return 0;
}

sd_event *sd_event_unref(sd_event *e) { return e; }
sd_event *sd_event_ref(sd_event *e) { return e; }
