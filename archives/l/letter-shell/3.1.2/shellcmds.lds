SECTIONS
{
  .shellCommand : { _shell_command_start = .; KEEP(*(shellCommand)) _shell_command_end = .; }
} INSERT AFTER .data;