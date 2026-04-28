export type { LexiconInstr, Syscall, SubReg } from './types'
export { LEXICON_INSTRS, SYSCALLS } from './lexicon'
export { SYSCALLS_FULL } from './syscalls'
export { INSTRUCTIONS_FULL } from './instructions'
export { SYSV_ABI, SYSCALL_CONVENTION, FUNC_CONVENTION, STACK_LAYOUT, NASM_DIRECTIVES, ASM_PATTERNS } from './conventions'
export type { RegRole, DirectiveInfo, PatternInfo } from './conventions'

// ── Mode-specific reference data ────────────────────────────
export { RIZIN_CMDS, RIZIN_CATS, ELF_FORMAT, ELF_SECTIONS, RE_PATTERNS } from './reference-re'
export type { RizinCmd, BinaryFormatInfo } from './reference-re'

export { PROTECTIONS, FORMAT_STRING_REF, PWNTOOLS_CHEATSHEET, PWN_TECHNIQUES } from './reference-pwn'
export type { ProtectionBypass, FormatStringRef, PwnTechnique, ShellcodeTemplate } from './reference-pwn'

export { GDB_CMDS, GDB_CATS, PWNDBG_CMDS, GDB_EXAMINE_FORMATS } from './reference-dbg'
export type { GdbCmd } from './reference-dbg'

export { BINWALK_OPTS, BINWALK_CATS, MAGIC_SIGNATURES, ENTROPY_GUIDE, FW_PATTERNS } from './reference-fw'
export type { BinwalkOpt, MagicSignature } from './reference-fw'

export { MODBUS_FUNCTIONS, MODBUS_REG_TYPES, MODBUS_EXCEPTIONS, MODBUS_FRAME, PROTOCOL_PATTERNS } from './reference-hw'
export type { ModbusFunc, ModbusRegType, ModbusException } from './reference-hw'
