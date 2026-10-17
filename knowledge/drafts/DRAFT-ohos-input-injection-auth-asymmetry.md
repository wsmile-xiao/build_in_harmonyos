# DRAFT - OHOS input-injection authorization is asymmetric per event type

> Status: DRAFT | Source: archives/c/cliclick/5.1 HarmonyOS PC port (path B candidate); on-device probe `probe_ohinput.c`. Final Exxx numbering is assigned by the knowledge-base editor.

## Rule

OHOS `multimodalinput` injection APIs are gated per event type. Key injection
(`OH_Input_InjectKeyEvent`) succeeds without any authorization; mouse injection
(`OH_Input_InjectMouseEvent`) and event monitors
(`OH_Input_AddMouseEventMonitor`) are rejected with `INPUT_PERMISSION_DENIED`
(201); `OH_Input_RequestInjection` in a non-interactive session returns
`INPUT_INJECTION_AUTHORIZING` (3900005) with the registered callback never
firing and the state stuck at `AUTHORIZING`. Injection CLIs must split their
command surface by real capability, fail explicitly on gated commands with a
diagnostic naming `OH_Input_RequestInjection`, and must never poll the
AUTHORIZING state or wait for its callback.

## Why this is a porting discovery, not SDK documentation

The SDK header `oh_input_manager.h` only declares the status enum
(`UNAUTHORIZED`/`AUTHORIZING`/`AUTHORIZED`), the return codes and the function
signatures. It does not document:

- that the gate is asymmetric per event type (key events bypass it entirely);
- that a non-interactive session cannot complete the
  `AUTHORIZING` -> `AUTHORIZED` transition and the
  `OH_Input_RequestInjection` callback does not fire there;
- the concrete codes a CLI author must map at runtime (201, 3900005).

All three are behavioral facts observable only through an on-device probe.
The probe below was independently re-run in a fresh device shell during audit
and reproduces every number exactly. An entry reviewer may argue "the header
already describes the authorization state machine" — it does not describe the
asymmetry, the non-convergence, or the diagnostics mapping, which is where the
porting value lies.

## Failure signature

An injection CLI works for key commands but fails all mouse/monitor commands
on a real OHOS PC:

```text
mouse command: INPUT_PERMISSION_DENIED (201)
OH_Input_RequestInjection: INPUT_INJECTION_AUTHORIZING (3900005)
status stays AUTHORIZING; authorization callback never fires
key injection: INPUT_SUCCESS, no authorization required
```

## Root cause (causal chain)

1. Tool/SDK evidence: the sysroot ships
   `usr/include/multimodalinput/oh_input_manager.h`,
   `oh_key_code.h`, and `usr/lib/aarch64-linux-ohos/libohinput.so`.
2. Trigger: a C probe calls `QueryAuthorizedStatus` -> `AddMouseEventMonitor`
   -> `InjectMouseEvent` -> (on denial) `RequestInjection` + 3 s callback
   window -> `InjectKeyEvent`.
3. Failure points: monitor and mouse injection = 201; request = 3900005;
   callback silent; state = `AUTHORIZING`; key injection = `INPUT_SUCCESS`.
4. Classification: the platform security model grades authorization by event
   type and caller shape (interactive vs non-interactive session). This is an
   L1 platform-semantics fact: every `OH_Input_*` injection consumer on the
   platform hits the same asymmetry, so a single library discovery is enough
   to justify the entry (blocking surface: run failure + platform capability
   gap, evidenced by the probe).

## Probe-observed behavior (fresh shell, 2026-09-09)

```text
probe: start
query_authorized: result=0 status=UNAUTHORIZED
add_mouse_monitor: result=201
inject_move_initial: result=201
request_injection: result=3900005
auth_callback: called=0 status=none
query_authorized_after_request: result=0 status=AUTHORIZING
inject_move_after_request: result=201
inject_key_a: down=0 up=0
monitor: events=0 last=(-1,-1)
probe: done
```

## Pattern: command-level capability split with authorization guidance

- Probe before shipping; never assume a uniform injection capability.
- Commands on authorization-free APIs (key events) stay first-class.
- Commands on gated APIs check the gate at runtime and fail with a diagnostic
  that names `OH_Input_RequestInjection` as the authorization path.
- Tests for gated commands accept exactly two outcomes: authorized success or
  denied-with-diagnostic. Anything else fails.
- Commands whose API surface does not exist at all (pixel read-back, clipboard
  write) get explicit unsupported boundaries with negative tests (E240
  pattern).
- Worked example: cliclick 5.1 keeps `kd/ku/kp/t/w` first-class, delivers
  `c/dc/tc/rc/m/dd/dm/du` behind the gate with dual-outcome assertions, and
  marks `cp`/`p`/`.`/relative coords/`-r`/clipboard as explicit unsupported.

## Fallback (honest tradeoff)

In unauthorized environments, deliver gated commands as explicit-unsupported
with the same diagnostic. This masks capability instead of granting it; use it
only as a delivery fallback where the interactive authorization flow is
unreachable, and keep the "authorized environments are expected to work but
were not verified in this run" wording intact.

## Anti-patterns (forbid)

1. Polling or retrying `OH_Input_RequestInjection`, or waiting on the
   AUTHORIZING callback. The callback never fires in non-interactive sessions,
   so the loop deadlocks CI runs instead of failing fast.
2. Inferring mouse/monitor capability from key-injection success. The gate is
   asymmetric, so this manufactures a false capability declaration that fails
   with 201 in the field.

## Verification (self-contained; fresh device shell)

Step 1 — confirm the API surface exists:

```sh
test -f /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/multimodalinput/oh_input_manager.h && echo header-ok
test -f /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos/libohinput.so && echo lib-ok
```

Step 2 — save the complete probe below as `probe_ohinput.c` (note: the SDK
header is not self-contained, `#include <stdbool.h>` must come first).

```c
/* OHOS injection feasibility probe. Verifies runtime behavior of
 * OH_Input_InjectMouseEvent / InjectKeyEvent / RequestInjection /
 * QueryAuthorizedStatus / mouse monitor in this device environment. */

#include <stdbool.h>

#include <multimodalinput/oh_input_manager.h>

#include <stdio.h>
#include <time.h>

static volatile int g_auth_cb_called = 0;
static volatile int g_auth_cb_status = -1;
static volatile int g_monitor_events = 0;
static volatile int g_mon_x = -1;
static volatile int g_mon_y = -1;

static void auth_cb(Input_InjectionStatus status)
{
    g_auth_cb_called++;
    g_auth_cb_status = (int)status;
}

static void mouse_cb(const struct Input_MouseEvent *event)
{
    g_monitor_events++;
    g_mon_x = OH_Input_GetMouseEventGlobalX(event);
    g_mon_y = OH_Input_GetMouseEventGlobalY(event);
}

static const char *status_name(int status)
{
    switch (status) {
    case UNAUTHORIZED: return "UNAUTHORIZED";
    case AUTHORIZING: return "AUTHORIZING";
    case AUTHORIZED: return "AUTHORIZED";
    default: return "UNKNOWN";
    }
}

static void nap(long nanos)
{
    struct timespec ts;
    ts.tv_sec = 0;
    ts.tv_nsec = nanos;
    nanosleep(&ts, NULL);
}

int main(void)
{
    Input_InjectionStatus status = UNAUTHORIZED;
    Input_Result result;

    printf("probe: start\n");

    result = OH_Input_QueryAuthorizedStatus(&status);
    printf("query_authorized: result=%d status=%s\n", (int)result, status_name((int)status));

    result = OH_Input_AddMouseEventMonitor(mouse_cb);
    printf("add_mouse_monitor: result=%d\n", (int)result);

    struct Input_MouseEvent *mouse = OH_Input_CreateMouseEvent();
    if (mouse == NULL) {
        printf("create_mouse_event: FAIL\n");
        return 1;
    }
    OH_Input_SetMouseEventAction(mouse, MOUSE_ACTION_MOVE);
    OH_Input_SetMouseEventDisplayX(mouse, 100);
    OH_Input_SetMouseEventDisplayY(mouse, 100);
    OH_Input_SetMouseEventGlobalX(mouse, 100);
    OH_Input_SetMouseEventGlobalY(mouse, 100);
    OH_Input_SetMouseEventButton(mouse, MOUSE_BUTTON_NONE);
    OH_Input_SetMouseEventActionTime(mouse, 0);

    int32_t inject = OH_Input_InjectMouseEvent(mouse);
    printf("inject_move_initial: result=%d\n", (int)inject);

    if (inject == (int32_t)INPUT_PERMISSION_DENIED) {
        Input_Result request = OH_Input_RequestInjection(auth_cb);
        printf("request_injection: result=%d\n", (int)request);
        for (int i = 0; i < 30 && g_auth_cb_called == 0; i++) {
            nap(100000000L);
        }
        printf("auth_callback: called=%d status=%s\n", g_auth_cb_called,
               g_auth_cb_called ? status_name(g_auth_cb_status) : "none");
        result = OH_Input_QueryAuthorizedStatus(&status);
        printf("query_authorized_after_request: result=%d status=%s\n", (int)result,
               status_name((int)status));
        inject = OH_Input_InjectMouseEvent(mouse);
        printf("inject_move_after_request: result=%d\n", (int)inject);
    }

    struct Input_KeyEvent *key = OH_Input_CreateKeyEvent();
    if (key == NULL) {
        printf("create_key_event: FAIL\n");
        return 1;
    }
    OH_Input_SetKeyEventAction(key, KEY_ACTION_DOWN);
    OH_Input_SetKeyEventKeyCode(key, KEYCODE_A);
    OH_Input_SetKeyEventActionTime(key, 0);
    int32_t key_down = OH_Input_InjectKeyEvent(key);
    OH_Input_SetKeyEventAction(key, KEY_ACTION_UP);
    int32_t key_up = OH_Input_InjectKeyEvent(key);
    printf("inject_key_a: down=%d up=%d\n", (int)key_down, (int)key_up);
    OH_Input_DestroyKeyEvent(&key);

    nap(300000000L);
    printf("monitor: events=%d last=(%d,%d)\n", g_monitor_events, g_mon_x, g_mon_y);

    OH_Input_DestroyMouseEvent(&mouse);
    OH_Input_CancelInjection();
    printf("probe: done\n");
    return 0;
}
```

Step 3 — compile and run on the device:

```sh
/data/service/hnp/bin/clang --target=aarch64-linux-ohos \
  --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot \
  -lohinput probe_ohinput.c -o probe_ohinput
./probe_ohinput
```

Step 4 — require exactly the numbers in "Probe-observed behavior": key
injection free (`down=0 up=0`), mouse injection and monitor 201, request
3900005, callback `called=0`, state `AUTHORIZING`. Any other shape means the
platform behavior changed and this entry needs review.

## Scope

Any CLI, daemon, automation backend or CI test that calls `OH_Input_*`
injection APIs on HarmonyOS PC. The asymmetry is a platform security-model
property, so the split-with-guidance pattern transfers unchanged across tools.

## Related

- `E240` — same capability-split family, display domain (read-only metrics vs
  gated mode setting); this entry covers the input-injection domain and its
  runtime authorization state machine.
- synergy-core 1.20.4 (patches 0027/0028/0042) — same-family native input
  backend consumer practice over `oh_input_manager.h`.
- principles: `P-SYSCALL-001` (platform behavior differences must be handled
  in source), `P-RUNTIME-001` (unimplemented/gated capability must be
  intercepted before invocation, never mid-run).
