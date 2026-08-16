# activity-aware-firefox

This package keeps separate Firefox profiles per desktop activity. The upstream
KDE Plasma provider remains supported. On OpenHarmony or another desktop that
does not implement KDE Activities, callers provide a stable context explicitly:

```bash
activityfirefox \
  --activity-id ohos-workspace-1 \
  --activity-name Development \
  --copy-type new
```

The same values may be exported as `ACTIVITY_AWARE_ID` and
`ACTIVITY_AWARE_NAME`. This does not claim that OpenHarmony implements KDE
Activities; it defines a small provider boundary that a launcher, system
parameter bridge, or workspace manager can populate.

For non-interactive verification:

```bash
activityfirefox --activity-id ohos-workspace-1 \
  --activity-name "Development 1" --probe-context
```

The probe prints the provider, original context and deterministic Firefox
profile key without requiring Firefox, X11, KDE, or a GUI dialog service.
