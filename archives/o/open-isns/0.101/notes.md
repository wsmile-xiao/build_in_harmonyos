# open-isns 0.101

- Builds the static `libisns` development library without optional OpenSSL
  authentication or OpenSLP discovery.
- The upstream suite contains 11 root-only daemon/network test programs. They
  are inventoried but are not executed in the unprivileged package consumer.
- The added consumer validates public status, portal parsing, and attribute-list
  APIs without starting a service or accessing privileged paths.
- Local OHOS arm64 `conan create` completed successfully: the static library
  and consumer both compiled and linked. The 11 upstream daemon/network cases
  require root, live services, and an OHOS device, so they are not runnable in
  the local unprivileged cross-build environment.
- Native OHOS builds place Autoconf's temporary directories and files under
  the worker's writable `TMPDIR` and use the repository's E011 `umask 022`
  workaround so `config.status` can create and read its generated awk programs
  on HMDFS.
- Official OHOS test and CI results remain pending.
