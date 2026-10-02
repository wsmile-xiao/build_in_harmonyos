# mlocate

`mlocate` provides the `locate` and `updatedb` commands for searching an indexed file-name database.

Upstream: https://pagure.io/mlocate

On HarmonyOS, create a user-owned database from an explicit root and output path, then query it:

```sh
updatedb -U "$HOME/data" -o "$HOME/mlocate.db" -l 0
locate -d "$HOME/mlocate.db" filename
```

The package does not rely on the upstream set-group-ID installation hook. Consumers choose a database they own with `updatedb -U` and `-o`.
