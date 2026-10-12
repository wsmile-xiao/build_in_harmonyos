# HarmonyOS Qt 6.0 Cross-UID Probe

This is a test-only HarmonyOS app. It uses its normal app sandbox UID to connect to the Qt test server and declares `ohos.permission.INTERNET`, required by the OpenHarmony Qt socket guidance for POSIX socket use. It does not need root.

## Build

Before opening the project, materialize its small app icons from the checked-in text asset:

```sh
python3 scripts/prepare_hap_resources.py
```

This keeps the PR source diff text-only because the GitCode PR diff endpoint omits binary patch payloads. The generated PNG files are ignored by Git. Then open this directory as a DevEco Studio project and build the `entry` module for `arm64-v8a`. The project uses the DevEco installation's HarmonyOS 6 SDK and Native C++ toolchain. Configure HarmonyOS debug signing locally in DevEco when installing to a device; generated credentials and profiles are not stored in this project.

## Run the device test

1. Install the signed HAP and launch the package twice using HarmonyOS app-clone indices 0 and 1.
2. In clone index 0, tap **Start Qt QLocalServer** and copy the displayed `server_full_name`.
3. In clone index 1, enter that exact endpoint and tap **Probe Qt QLocalSocket**.
4. Refresh the primary server status after the request. Save both reports.

The cross-UID filtering test passes when the clone client connects, reads the primary UID through `SO_PEERCRED`, and sends its payload, while the primary server remains active but reports no accepted Qt connection, no payload, and no response. The same-UID control sends a request from clone index 0 and verifies the complete Qt echo round-trip.

On HarmonyOS 6.0, the fixed implementation passed with primary UID `20020151` and clone UID `20020152`. The client connected and sent 47 bytes; the reset primary server reported `server_accepted=false` and `payload_bytes=0`. The separate SSH-system-UID probe returned `EACCES` before Qt because it crosses a HarmonyOS security-domain boundary; that result is not used as the app-clone test result. Evidence and the signed HAP hash are recorded in `../MANIFEST.yml` and `.ci_logs/qt6-6.0-device-20261010/`.
