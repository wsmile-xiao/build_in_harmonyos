# Copyright © 2026 The Mesa OHOS port
# SPDX-License-Identifier: MIT
#
# rule12 HarmonyOS PC consumer end-to-end test.
#
# Drives the real public EGL + GLESv2 entry points exported by the libraries
# this recipe packages, exercises the two util/ OHOS adaptations, and asserts
# on rendered pixels.  Built as a normal Mesa tree target so it links the same
# objects that get installed.

ohos_egl_e2e = executable(
  'ohos_egl_e2e',
  files('ohos_egl_e2e.c'),
  include_directories : [inc_include, inc_src, inc_util, inc_gallium, inc_gallium_aux],
  link_with : [libegl, libgles2],
  dependencies : [idep_mesautil, dep_thread, dep_dl],
  install : false,
)

test(
  'ohos_egl_e2e',
  ohos_egl_e2e,
  suite : ['ohos'],
  timeout : 120,
)
