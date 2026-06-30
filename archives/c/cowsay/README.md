# cowsay

cowsay is a configurable talking cow, originally written in Perl by Tony Monroe.

This project (version 1.5.0) is a translation in JavaScript of the original program, adapted for OpenHarmony.

## Description

cowsay generates ASCII art of a cow saying or thinking a message. It's a fun utility for displaying text in a whimsical way.

## Version History

- 1.5.0: JavaScript implementation (current)
- Original: Perl implementation (historical)

## Installation on OpenHarmony

This package requires Node.js runtime to execute. After installing Node.js:

```bash
# Install cowsay
tar -xzf cowsay-1.5.0-ohos-aarch64.tar.gz
# Follow the installation instructions
```

## Usage

```bash
cowsay "Hello from OpenHarmony!"
```

Output:
```
 ____________________
< Hello from OpenHarmony! >
 ------------------
        \   ^__^
         \  (oo)\_______
            (__)\\       )\\/\\
                ||----w |
                ||     ||
```

## Dependencies

- Node.js runtime (user must install separately)

## License

MIT License

## Original Author

Fabio Crisci (piuccio@gmail.com)
https://github.com/piuccio/cowsay

## OpenHarmony Adaptation

This version has been packaged for OpenHarmony using custom build files to wrap the Node.js package structure.