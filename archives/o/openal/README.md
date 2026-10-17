# OpenAL Soft

OpenAL Soft is a software implementation of the OpenAL 3D audio API.

## HarmonyOS PC Adaptation

The HarmonyOS PC recipe packages the library and validates its core API with an
adapted upstream scenario and an installed-package consumer. The OHOS build
enables libc++15 ranges through the toolchain definition and includes the local
compatibility helper only where it is used.

## Upstream

- Source: https://github.com/kcat/openal-soft
