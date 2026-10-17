# rpm2cpio

A shell script that converts RPM packages to cpio archives. It uses `tar` (bsdtar/libarchive) to extract the cpio payload from an RPM file.

## Source

- Official source: [FreeBSD ports — archivers/rpm2cpio](https://cgit.freebsd.org/ports/tree/archivers/rpm2cpio)
- The tool is a single shell script (`rpm2cpio.sh`) with no compilation step.

## Usage

```sh
rpm2cpio file.rpm | cpio -idv
```

## Runtime Dependencies

- `bsdtar` / `libarchive` v2.8+

## OHOS Adaptation Notes

- No compilation required (shell script).
- Uses symbolic links instead of hard links due to HMDFS limitations (R5).
