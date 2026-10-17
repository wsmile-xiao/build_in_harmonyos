/* Minimal 8086 C program used to exercise the dev86 toolchain:
 * bcc -S  -> as86 -> ld86 -> objdump86
 * NOTE: bcc is a K&R-style 8086 compiler: use empty () not (void).
 */
int main() { return 42; }
