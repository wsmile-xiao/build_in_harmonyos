# GameNetworkingSockets

Valve's GameNetworkingSockets library for HarmonyOS PC: reliable UDP
transport for games, extracted from the technology behind
SteamNetworkingSockets. 1.6.0 is the first adapted release.

The build uses the OpenSSL crypto backend (registry `openssl/3.5.8.1`)
with protobuf-based wire protocol serialization (registry `protobuf/33.6.1`,
which also ships the protoc generator). Native ICE P2P support is enabled
(upstream default `ENABLE_ICE=ON`: the native ICE client is a pure POSIX
implementation needing no submodule). The WebRTC-based ICE variant stays
disabled (`USE_STEAMWEBRTC=OFF`): the webrtc submodule is not shipped in
the release tarball and its pinned abseil (lts_2020_02_25) conflicts with
protobuf 33.x's abseil. The core reliable-UDP client/server surface is
unaffected.
