/* Minimal stub of termkey.h (libtermkey) for OHOS (not published).
 * Types/functions used by vis; implementations in stub-termkey.c.
 * SPDX-License-Identifier: ISC */
#ifndef TERMKEY_STUB_H
#define TERMKEY_STUB_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

#define TERMKEY_VERSION 0x000900
#define TERMKEY_CHECK_VERSION \
    if (termkey_get_version() < TERMKEY_VERSION) { return -1; }

typedef struct TermKey TermKey;

typedef enum {
    TERMKEY_TYPE_UNICODE,
    TERMKEY_TYPE_FUNCTION,
    TERMKEY_TYPE_KEYSYM,
    TERMKEY_TYPE_MOUSE,
    TERMKEY_TYPE_UNKNOWN_CSI,
    TERMKEY_TYPE_UNKNOWN_UTF8,
    TERMKEY_TYPE_UNKNOWN_BYTES
} TermKeyType;

typedef enum {
    TERMKEY_SYM_UNKNOWN,
    TERMKEY_SYM_NONE,
    TERMKEY_SYM_ESCAPE,
    TERMKEY_SYM_BACKSPACE,
    TERMKEY_SYM_TAB,
    TERMKEY_SYM_ENTER,
    TERMKEY_SYM_SPACE,
    TERMKEY_SYM_DEL,
    TERMKEY_SYM_UP,
    TERMKEY_SYM_DOWN,
    TERMKEY_SYM_LEFT,
    TERMKEY_SYM_RIGHT,
    TERMKEY_SYM_HOME,
    TERMKEY_SYM_END,
    TERMKEY_SYM_PAGEUP,
    TERMKEY_SYM_PAGEDOWN,
    TERMKEY_SYM_INSERT,
    TERMKEY_SYM_ESCAPE2,
    TERMKEY_SYM_BEGIN,
    TERMKEY_SYM_FIND,
    TERMKEY_SYM_DELETE,
    TERMKEY_SYM_SELECT,
    TERMKEY_SYM_CANCEL,
    TERMKEY_SYM_CLEAR,
    TERMKEY_SYM_CLOSE,
    TERMKEY_SYM_COMMAND,
    TERMKEY_SYM_COPY,
    TERMKEY_SYM_CUT,
    TERMKEY_SYM_EXIT,
    TERMKEY_SYM_HELP,
    TERMKEY_SYM_MARK,
    TERMKEY_SYM_MESSAGE,
    TERMKEY_SYM_MOUSE,
    TERMKEY_SYM_MOVE,
    TERMKEY_SYM_NEXT,
    TERMKEY_SYM_OPEN,
    TERMKEY_SYM_OPTIONS,
    TERMKEY_SYM_PREVIOUS,
    TERMKEY_SYM_PRINT,
    TERMKEY_SYM_REDO,
    TERMKEY_SYM_RESUME,
    TERMKEY_SYM_SAVE,
    TERMKEY_SYM_SUSPEND,
    TERMKEY_SYM_UNDO,
    TERMKEY_SYM_F1, TERMKEY_SYM_F2, TERMKEY_SYM_F3, TERMKEY_SYM_F4,
    TERMKEY_SYM_F5, TERMKEY_SYM_F6, TERMKEY_SYM_F7, TERMKEY_SYM_F8,
    TERMKEY_SYM_F9, TERMKEY_SYM_F10, TERMKEY_SYM_F11, TERMKEY_SYM_F12,
    TERMKEY_SYM_KPCOMMA, TERMKEY_SYM_KPEQUALS,
    TERMKEY_SYM_KPPLUS, TERMKEY_SYM_KPMINUS, TERMKEY_SYM_KPMULT,
    TERMKEY_SYM_KPDIV, TERMKEY_SYM_KPENTER, TERMKEY_SYM_KPPERIOD,
    TERMKEY_SYM_KP,
    TERMKEY_SYM_KP0,
    TERMKEY_SYM_KP1,
    TERMKEY_SYM_KP2,
    TERMKEY_SYM_KP3,
    TERMKEY_SYM_KP4,
    TERMKEY_SYM_KP5,
    TERMKEY_SYM_KP6,
    TERMKEY_SYM_KP7,
    TERMKEY_SYM_KP8,
    TERMKEY_SYM_KP9,
    TERMKEY_SYM_REFERENCE,
    TERMKEY_SYM_REFRESH,
    TERMKEY_SYM_REPLACE,
    TERMKEY_SYM_RESTART,
    TERMKEY_SYM_MAX
} TermKeySym;

typedef enum {
    TERMKEY_RES_NONE,
    TERMKEY_RES_KEY,
    TERMKEY_RES_EOF,
    TERMKEY_RES_AGAIN,
    TERMKEY_RES_ERROR,
    TERMKEY_RES_UNKNOWN,
    TERMKEY_RES_CANCEL
} TermKeyResult;

typedef enum {
    TERMKEY_FORMAT_VIM = 1,
    TERMKEY_FORMAT_ALT = 2,
    TERMKEY_FORMAT_LONGMOD = 4,
    TERMKEY_FORMAT_SPACEMOD = 8,
    TERMKEY_FORMAT_CARETCTRL = 16,
    TERMKEY_FORMAT_LOWERMOD = 32,
    TERMKEY_FORMAT_UTF8 = 64
} TermKeyFormat;

typedef enum {
    TERMKEY_CANON_NONE = 0,
    TERMKEY_CANON_DELBS = 1,
    TERMKEY_CANON_SPACESYMBOL = 2
} TermKeyCanonFlags;

/* termkey_new flags */
#define TERMKEY_FLAG_UTF8        0x0001
#define TERMKEY_FLAG_SPACESYMBOL 0x0002
#define TERMKEY_FLAG_CTRLCHARS   0x0004
#define TERMKEY_FLAG_RAW         0x0008
#define TERMKEY_FLAG_CONVERTKP   0x0010
#define TERMKEY_FLAG_LINEMODE    0x0020
#define TERMKEY_FLAG_MOUSE       0x0040
#define TERMKEY_FLAG_CURSORPOS   0x0080
#define TERMKEY_FLAG_ALTSCREEN   0x0100


typedef enum {
    TERMKEY_MOUSE_UNKNOWN,
    TERMKEY_MOUSE_PRESS,
    TERMKEY_MOUSE_DRAG,
    TERMKEY_MOUSE_RELEASE
} TermKeyMouseEvent;

typedef enum {
    TERMKEY_KEYCODE_UNKNOWN,
    TERMKEY_KEYCODE_MAX
} TermKeyKeycodeEvent;

typedef struct TermKeyKey {
    TermKeyType type;
    union {
        uint32_t codepoint;
        TermKeySym sym;
        struct {
            TermKeyMouseEvent event;
            int button;
        } mouse;
        TermKeyKeycodeEvent code;
        struct {
            int cmd;
            int arg;
        } csi;
    } code;
    char utf8[7];  /* direct member (vis uses key.utf8) */
    int modifiers;
} TermKeyKey;

typedef struct TermKeyPos {
    int x, y;
} TermKeyPos;

typedef struct TermKeyMouseEventInfo {
    TermKeyPos pos;
    int button;
    int line;
    int col;
    TermKeyMouseEvent type;
} TermKeyMouseEventInfo;

#ifdef __cplusplus
extern "C" {
#endif

unsigned long termkey_get_version(void);
TermKey *termkey_new(int fd, int flags);
TermKey *termkey_new_abstract(const char *term, int flags);
void termkey_free(TermKey *tk);
void termkey_destroy(TermKey *tk);
int termkey_start(TermKey *tk);
int termkey_stop(TermKey *tk);
void termkey_reopen(TermKey *tk, int fd, int flags);
size_t termkey_push_bytes(TermKey *tk, const char *bytes, size_t len);
size_t termkey_interpret_key(TermKey *tk, char *buffer, size_t buflen,
                             int flags, TermKeyResult *result);
TermKeyResult termkey_getkey(TermKey *tk, TermKeyKey *key);
TermKeyResult termkey_getkey_force(TermKey *tk, TermKeyKey *key);
TermKeyResult termkey_waitkey(TermKey *tk, TermKeyKey *key);
TermKeyResult termkey_getkey_force_sse(TermKey *tk, TermKeyKey *key);
int termkey_advisereadable(TermKey *tk);
size_t termkey_get_buffer_remaining(TermKey *tk);
int termkey_get_waittime(TermKey *tk);
int termkey_set_waittime(TermKey *tk, int waittime);
int termkey_get_canonflags(TermKey *tk);
int termkey_set_canonflags(TermKey *tk, int flags);
int termkey_get_flags(TermKey *tk);
int termkey_set_flags(TermKey *tk, int flags);
size_t termkey_strfkey(TermKey *tk, char *buffer, size_t len,
                       TermKeyKey *key, int flags);
const char *termkey_strpkey(TermKey *tk, const char *str, TermKeyKey *key,
                           int flags);
const char *termkey_get_keyname(TermKey *tk, TermKeySym sym);
TermKeySym termkey_keyname2sym(const char *keyname);
int termkey_interpret_csi(TermKey *tk, TermKeyKey *key, long *args,
                          size_t *nargs, unsigned long *cmd);
size_t termkey_interpret_mouse(TermKey *tk, const char *buffer, size_t len,
                               TermKeyMouseEventInfo *info, int *flags);
int termkey_parse_darwin(TermKey *tk, TermKeyKey *key, const char *buffer,
                         size_t len);

#ifdef __cplusplus
}
#endif

#endif /* TERMKEY_STUB_H */

/* key modifiers */
#define TERMKEY_KEYMOD_SHIFT 0x01
#define TERMKEY_KEYMOD_ALT   0x02
#define TERMKEY_KEYMOD_CTRL  0x04
#define TERMKEY_KEYMOD_META  0x08
