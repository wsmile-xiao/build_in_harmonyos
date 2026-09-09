# HarmonyOS PC G2 attempt 2

- Run ID: `20260904T174039Z-44797`
- Result archive: `output/pygame-2.6.1/3pygame-device-results.tar.gz`
- Result archive SHA-256: `66ab41d82cf8c29806c12e7262180f6f92e7a51ad24d73148fc7ff0099b38612`
- Preceding gates: language preflight PASS; W0 10/10 direct references PASS;
  private SDL2 runtime ELF validation PASS
- G2 exit code: 1

The first pygame compile edge failed at `src_c/_sdl2/sdl2.c:1237`:

```text
fatal error: 'SDL.h' file not found
```

The published SDL-family package metadata exposed `include/`, while its
headers are installed under `include/SDL2/` and pygame's upstream `_sdl2`
sources include `SDL.h` directly. The recipe now adds the existing concrete
`include/SDL2` directory to every SDL-family dependency's generated Setup
include list. No source patch is required.
