# dmg2img 1.6.7 Release Note

## Version
- dmg2img: v1.6.7
- vfdecrypt: included

## Changes from upstream
- OpenSSL 1.1.1 API compatibility patch for vfdecrypt

## Dependencies
- zlib >= 1.3.1
- bzip2 >= 1.0.8
- openssl >= 1.1.1w (for vfdecrypt)

## Usage
```bash
dmg2img [-l] [-p N] [-s] [-v] [-V] [-d] <input.dmg> [<output.img>]
vfdecrypt [-e] [-p password] [-k key] -i in-file -o out-file
```
