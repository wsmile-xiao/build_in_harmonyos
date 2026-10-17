# Activity Log Manager

Activity Log Manager is a GTK desktop application for reviewing and controlling
the activity data recorded by Zeitgeist.

## OHOS adaptation

- Builds as a standalone GTK application with optional Whoopsie,
  gnome-control-center, Switchboard, and NLS integrations disabled.
- The legacy Autotools release accepts the HarmonyOS Linux triplet through
  package-local source patches.
- Desktop entry generation uses a deterministic local rule because the release
  requires legacy intltool during configuration.

## Dependencies

| Dependency | Purpose |
|---|---|
| libgee/0.6.8 | Gee 1.0 collection API |
| libzeitgeist/1.0.4 | Zeitgeist 2.0 API |
| gtk/3.24.43 | GTK 3 desktop UI |
| glib/2.84.0 | GLib, GObject, and GIO |
| vala/0.56.18 | Build tool for possible Vala regeneration |

## Reference

- Upstream: https://launchpad.net/activity-log-manager
- Source release: https://launchpad.net/activity-log-manager/0.9/0.9.7/+download/activity-log-manager-0.9.7.tar.xz
