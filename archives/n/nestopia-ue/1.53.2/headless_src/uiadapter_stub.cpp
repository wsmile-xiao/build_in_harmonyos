/*
Copyright (c) 2026 Nestopia UE OHOS PC adaptation contributors

No-op UiAdapter implementation for the headless build.

The upstream inputmanager.cpp forwards UI actions (fullscreen, pause,
mute, screenshot, quit, ...) through UiAdapter, whose real implementation
(uiadapter.cpp) drives the FLTK GUI.  In the headless build the GUI is
excluded, so these calls become no-ops.

Licensed under the same terms as Nestopia UE (GPL-2.0-or-later).
*/
#include "uiadapter.h"

void UiAdapter::fullscreen() {}
void UiAdapter::fastforward(bool) {}
void UiAdapter::pause() {}
void UiAdapter::mute() {}
void UiAdapter::screenshot() {}
void UiAdapter::quit() {}
void UiAdapter::show_inputmsg(int) {}
