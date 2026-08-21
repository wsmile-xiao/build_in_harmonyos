/* Auto-generated stub implementations matching real systemd 261 sd-varlink.h */
#include <stdint.h>
#include <sys/types.h>
#include <stdarg.h>
#include <stddef.h>
#include "systemd/sd-varlink.h"
#include "systemd/sd-event.h"

int sd_varlink_connect_address(sd_varlink **ret, const char *address) {
    (void) ret; (void) address;
    return 0;
}
int sd_varlink_connect_exec(sd_varlink **ret, const char *command, char **argv) {
    (void) ret; (void) command; (void) argv;
    return 0;
}
int sd_varlink_connect_url(sd_varlink **ret, const char *url) {
    (void) ret; (void) url;
    return 0;
}
int sd_varlink_connect_fd(sd_varlink **ret, int fd) {
    (void) ret; (void) fd;
    return 0;
}
int sd_varlink_connect_fd_pair(sd_varlink **ret, int input_fd, int output_fd, const struct ucred *override_ucred) {
    (void) ret; (void) input_fd; (void) output_fd; (void) override_ucred;
    return 0;
}
int sd_varlink_get_fd(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_get_input_fd(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_get_output_fd(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_get_events(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_get_timeout(sd_varlink *v, uint64_t *ret) {
    (void) v; (void) ret;
    return 0;
}
int sd_varlink_attach_event(sd_varlink *v, sd_event *e, int64_t priority) {
    (void) v; (void) e; (void) priority;
    return 0;
}
void sd_varlink_detach_event(sd_varlink *v) {
    (void) v;
}
int sd_varlink_process(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_wait(sd_varlink *v, uint64_t timeout) {
    (void) v; (void) timeout;
    return 0;
}
int sd_varlink_is_idle(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_is_connected(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_flush(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_close(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_send(sd_varlink *v, const char *method, sd_json_variant *parameters) {
    (void) v; (void) method; (void) parameters;
    return 0;
}
int sd_varlink_sendb(sd_varlink *v, const char *method, ...) {
    (void) v; (void) method;
    return 0;
}
int sd_varlink_call_full(sd_varlink *v, const char *method, sd_json_variant *parameters, sd_json_variant **ret_parameters, const char **ret_error_id, sd_varlink_reply_flags_t *ret_flags) {
    (void) v; (void) method; (void) parameters; (void) ret_parameters; (void) ret_error_id; (void) ret_flags;
    return 0;
}
int sd_varlink_call(sd_varlink *v, const char *method, sd_json_variant *parameters, sd_json_variant **ret_parameters, const char **ret_error_id) {
    (void) v; (void) method; (void) parameters; (void) ret_parameters; (void) ret_error_id;
    return 0;
}
int sd_varlink_callb_ap(sd_varlink *v, const char *method, sd_json_variant **ret_parameters, const char **ret_error_id, sd_varlink_reply_flags_t *ret_flags, va_list ap) {
    (void) v; (void) method; (void) ret_parameters; (void) ret_error_id; (void) ret_flags; (void) ap;
    return 0;
}
int sd_varlink_callb_full(sd_varlink *v, const char *method, sd_json_variant **ret_parameters, const char **ret_error_id, sd_varlink_reply_flags_t *ret_flags, ...) {
    (void) v; (void) method; (void) ret_parameters; (void) ret_error_id; (void) ret_flags;
    return 0;
}
int sd_varlink_callb(sd_varlink *v, const char *method, sd_json_variant **ret_parameters, const char **ret_error_id, ...) {
    (void) v; (void) method; (void) ret_parameters; (void) ret_error_id;
    return 0;
}
int sd_varlink_call_and_upgrade(sd_varlink *v, const char *method, sd_json_variant *parameters, sd_json_variant **ret_parameters, const char **ret_error_id, int *ret_input_fd, int *ret_output_fd) {
    (void) v; (void) method; (void) parameters; (void) ret_parameters; (void) ret_error_id; (void) ret_input_fd; (void) ret_output_fd;
    return 0;
}
int sd_varlink_collect_full(sd_varlink *v, const char *method, sd_json_variant *parameters, sd_json_variant **ret_parameters, const char **ret_error_id, sd_varlink_reply_flags_t *ret_flags) {
    (void) v; (void) method; (void) parameters; (void) ret_parameters; (void) ret_error_id; (void) ret_flags;
    return 0;
}
int sd_varlink_collect(sd_varlink *v, const char *method, sd_json_variant *parameters, sd_json_variant **ret_parameters, const char **ret_error_id) {
    (void) v; (void) method; (void) parameters; (void) ret_parameters; (void) ret_error_id;
    return 0;
}
int sd_varlink_collectb(sd_varlink *v, const char *method, sd_json_variant **ret_parameters, const char **ret_error_id, ...) {
    (void) v; (void) method; (void) ret_parameters; (void) ret_error_id;
    return 0;
}
int sd_varlink_invoke(sd_varlink *v, const char *method, sd_json_variant *parameters) {
    (void) v; (void) method; (void) parameters;
    return 0;
}
int sd_varlink_invokeb(sd_varlink *v, const char *method, ...) {
    (void) v; (void) method;
    return 0;
}
int sd_varlink_observe(sd_varlink *v, const char *method, sd_json_variant *parameters) {
    (void) v; (void) method; (void) parameters;
    return 0;
}
int sd_varlink_observeb(sd_varlink *v, const char *method, ...) {
    (void) v; (void) method;
    return 0;
}
int sd_varlink_reply(sd_varlink *v, sd_json_variant *parameters) {
    (void) v; (void) parameters;
    return 0;
}
int sd_varlink_replyb(sd_varlink *v, ...) {
    (void) v;
    return 0;
}
int sd_varlink_reply_and_upgrade(sd_varlink *v, sd_json_variant *parameters, int *ret_input_fd, int *ret_output_fd) {
    (void) v; (void) parameters; (void) ret_input_fd; (void) ret_output_fd;
    return 0;
}
int sd_varlink_error(sd_varlink *v, const char *error_id, sd_json_variant *parameters) {
    (void) v; (void) error_id; (void) parameters;
    return 0;
}
int sd_varlink_errorb(sd_varlink *v, const char *error_id, ...) {
    (void) v; (void) error_id;
    return 0;
}
int sd_varlink_error_invalid_parameter(sd_varlink *v, sd_json_variant *parameters) {
    (void) v; (void) parameters;
    return 0;
}
int sd_varlink_error_invalid_parameter_name(sd_varlink *v, const char *name) {
    (void) v; (void) name;
    return 0;
}
int sd_varlink_error_errno(sd_varlink *v, int error) {
    (void) v; (void) error;
    return 0;
}
int sd_varlink_notify(sd_varlink *v, sd_json_variant *parameters) {
    (void) v; (void) parameters;
    return 0;
}
int sd_varlink_notifyb(sd_varlink *v, ...) {
    (void) v;
    return 0;
}
int sd_varlink_dispatch_again(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_get_current_method(sd_varlink *v, const char **ret) {
    (void) v; (void) ret;
    return 0;
}
int sd_varlink_get_current_parameters(sd_varlink *v, sd_json_variant **ret) {
    (void) v; (void) ret;
    return 0;
}
int sd_varlink_dispatch(sd_varlink *v, sd_json_variant *parameters, const sd_json_dispatch_field dispatch_table[], void *userdata) {
    (void) v; (void) parameters; (void) dispatch_table; (void) userdata;
    return 0;
}
int sd_varlink_push_fd(sd_varlink *v, int fd) {
    (void) v; (void) fd;
    return 0;
}
int sd_varlink_push_dup_fd(sd_varlink *v, int fd) {
    (void) v; (void) fd;
    return 0;
}
int sd_varlink_reset_fds(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_peek_fd(sd_varlink *v, size_t i) {
    (void) v; (void) i;
    return 0;
}
int sd_varlink_peek_dup_fd(sd_varlink *v, size_t i) {
    (void) v; (void) i;
    return 0;
}
int sd_varlink_take_fd(sd_varlink *v, size_t i) {
    (void) v; (void) i;
    return 0;
}
int sd_varlink_get_n_fds(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_set_allow_fd_passing_input(sd_varlink *v, int b) {
    (void) v; (void) b;
    return 0;
}
int sd_varlink_set_allow_fd_passing_output(sd_varlink *v, int b) {
    (void) v; (void) b;
    return 0;
}
int sd_varlink_bind_reply(sd_varlink *v, sd_varlink_reply_t reply) {
    (void) v; (void) reply;
    return 0;
}
int sd_varlink_set_sentinel(sd_varlink *v, const char *error_id) {
    (void) v; (void) error_id;
    return 0;
}
int sd_varlink_get_peer_uid(sd_varlink *v, uid_t *ret) {
    (void) v; (void) ret;
    return 0;
}
int sd_varlink_get_peer_gid(sd_varlink *v, gid_t *ret) {
    (void) v; (void) ret;
    return 0;
}
int sd_varlink_get_peer_pid(sd_varlink *v, pid_t *ret) {
    (void) v; (void) ret;
    return 0;
}
int sd_varlink_get_peer_pidfd(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_set_relative_timeout(sd_varlink *v, uint64_t timeout) {
    (void) v; (void) timeout;
    return 0;
}
int sd_varlink_set_description(sd_varlink *v, const char *d) {
    (void) v; (void) d;
    return 0;
}
int sd_varlink_set_input_sensitive(sd_varlink *v) {
    (void) v;
    return 0;
}
int sd_varlink_server_new(sd_varlink_server **ret, sd_varlink_server_flags_t flags) {
    (void) ret; (void) flags;
    return 0;
}
int sd_varlink_server_set_info(sd_varlink_server *s,
                const char *vendor,
                const char *product,
                const char *version,
                const char *url) {
    (void) s; (void) vendor; (void) product; (void) version; (void) url;
    return 0;
}
int sd_varlink_server_listen_address(sd_varlink_server *s, const char *address, mode_t mode) {
    (void) s; (void) address; (void) mode;
    return 0;
}
int sd_varlink_server_listen_fd(sd_varlink_server *s, int fd) {
    (void) s; (void) fd;
    return 0;
}
int sd_varlink_server_listen_auto(sd_varlink_server *s) {
    (void) s;
    return 0;
}
int sd_varlink_server_listen_name(sd_varlink_server *s, const char *name) {
    (void) s; (void) name;
    return 0;
}
int sd_varlink_server_add_connection(sd_varlink_server *s, int fd, sd_varlink **ret) {
    (void) s; (void) fd; (void) ret;
    return 0;
}
int sd_varlink_server_add_connection_pair(sd_varlink_server *s, int input_fd, int output_fd, const struct ucred *override_ucred, sd_varlink **ret) {
    (void) s; (void) input_fd; (void) output_fd; (void) override_ucred; (void) ret;
    return 0;
}
int sd_varlink_server_add_connection_stdio(sd_varlink_server *s, sd_varlink **ret) {
    (void) s; (void) ret;
    return 0;
}
int sd_varlink_server_bind_method(sd_varlink_server *s, const char *method, sd_varlink_method_t callback) {
    (void) s; (void) method; (void) callback;
    return 0;
}
int sd_varlink_server_bind_method_many_internal(sd_varlink_server *s, ...) {
    (void) s;
    return 0;
}
int sd_varlink_server_bind_connect(sd_varlink_server *s, sd_varlink_connect_t connect) {
    (void) s; (void) connect;
    return 0;
}
int sd_varlink_server_bind_disconnect(sd_varlink_server *s, sd_varlink_disconnect_t disconnect) {
    (void) s; (void) disconnect;
    return 0;
}
int sd_varlink_server_add_interface(sd_varlink_server *s, const sd_varlink_interface *interface) {
    (void) s; (void) interface;
    return 0;
}
int sd_varlink_server_add_interface_many_internal(sd_varlink_server *s, ...) {
    (void) s;
    return 0;
}
int sd_varlink_server_attach_event(sd_varlink_server *s, sd_event *e, int64_t priority) {
    (void) s; (void) e; (void) priority;
    return 0;
}
int sd_varlink_server_detach_event(sd_varlink_server *s) {
    (void) s;
    return 0;
}
int sd_varlink_server_loop_auto(sd_varlink_server *server) {
    (void) server;
    return 0;
}
int sd_varlink_server_shutdown(sd_varlink_server *server) {
    (void) server;
    return 0;
}
int sd_varlink_server_set_exit_on_idle(sd_varlink_server *s, int b) {
    (void) s; (void) b;
    return 0;
}
int sd_varlink_server_set_connections_per_uid_max(sd_varlink_server *s, unsigned m) {
    (void) s; (void) m;
    return 0;
}
int sd_varlink_server_set_connections_max(sd_varlink_server *s, unsigned m) {
    (void) s; (void) m;
    return 0;
}
int sd_varlink_server_set_description(sd_varlink_server *s, const char *description) {
    (void) s; (void) description;
    return 0;
}
int sd_varlink_invocation(sd_varlink_invocation_flags_t flags) {
    (void) flags;
    return 0;
}
int sd_varlink_error_to_errno(const char *error, sd_json_variant *parameters) {
    (void) error; (void) parameters;
    return 0;
}
int sd_varlink_error_is_invalid_parameter(const char *error, sd_json_variant *parameter, const char *name) {
    (void) error; (void) parameter; (void) name;
    return 0;
}


void *sd_varlink_server_set_userdata(sd_varlink_server *s, void *userdata) {
    (void) s; (void) userdata;
    return NULL;
}

unsigned sd_varlink_server_current_connections(sd_varlink_server *s) {
    (void) s;
    return 0;
}

void *sd_varlink_set_userdata(sd_varlink *v, void *userdata) {
    (void) v; (void) userdata;
    return NULL;
}
