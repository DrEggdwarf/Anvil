/**
 * x86-64 calling conventions, ABI info, register maps, and NASM directives.
 */

// ── System V AMD64 ABI (Linux, macOS, BSD) ──────────────────

export interface RegRole {
  reg: string
  role: string
  callerSaved: boolean
  desc: string
}

export const SYSV_ABI: RegRole[] = [
  { reg: 'rax', role: 'Return value', callerSaved: true, desc: 'Valeur de retour (et numero de syscall)' },
  { reg: 'rbx', role: 'General', callerSaved: false, desc: 'Callee-saved. Preserve a travers les appels.' },
  { reg: 'rcx', role: 'Arg 4 (syscall: detruit)', callerSaved: true, desc: '4e arg de fonction. Detruit par SYSCALL (remplace par R10).' },
  { reg: 'rdx', role: 'Arg 3 / Retour hi', callerSaved: true, desc: '3e arg. Aussi partie haute de retour 128-bit (rdx:rax).' },
  { reg: 'rsi', role: 'Arg 2', callerSaved: true, desc: '2e argument de fonction et de syscall.' },
  { reg: 'rdi', role: 'Arg 1', callerSaved: true, desc: '1er argument de fonction et de syscall.' },
  { reg: 'rbp', role: 'Frame pointer', callerSaved: false, desc: 'Base de la stack frame. Callee-saved. Optionnel avec -fomit-frame-pointer.' },
  { reg: 'rsp', role: 'Stack pointer', callerSaved: false, desc: 'Sommet de la stack. Doit etre aligne a 16 octets avant CALL.' },
  { reg: 'r8', role: 'Arg 5', callerSaved: true, desc: '5e argument de fonction et de syscall.' },
  { reg: 'r9', role: 'Arg 6', callerSaved: true, desc: '6e argument de fonction et de syscall.' },
  { reg: 'r10', role: 'Arg 4 (syscall)', callerSaved: true, desc: '4e arg de syscall (remplace RCX). Caller-saved en fonctions.' },
  { reg: 'r11', role: 'Flags (syscall: detruit)', callerSaved: true, desc: 'Detruit par SYSCALL (RFLAGS sauve ici). Caller-saved.' },
  { reg: 'r12', role: 'General', callerSaved: false, desc: 'Callee-saved. Preserve a travers les appels.' },
  { reg: 'r13', role: 'General', callerSaved: false, desc: 'Callee-saved.' },
  { reg: 'r14', role: 'General', callerSaved: false, desc: 'Callee-saved.' },
  { reg: 'r15', role: 'General', callerSaved: false, desc: 'Callee-saved.' },
]

// ── Syscall convention ──────────────────────────────────────

export const SYSCALL_CONVENTION = {
  title: 'Convention Syscall Linux x86-64',
  mechanism: 'Instruction SYSCALL (rapide, remplace int 0x80 en 64-bit)',
  number: 'RAX = numero du syscall',
  args: ['RDI = arg1', 'RSI = arg2', 'RDX = arg3', 'R10 = arg4 (pas RCX !)', 'R8 = arg5', 'R9 = arg6'],
  ret: 'RAX = valeur de retour (-errno en cas d\'erreur)',
  clobbered: ['RCX (sauvegarde de RIP)', 'R11 (sauvegarde de RFLAGS)'],
  notes: [
    'Max 6 arguments par registre, jamais par la stack',
    'Les registres callee-saved (RBX, RBP, R12-R15) sont preserves',
    'int 0x80 utilise l\'ABI 32-bit meme en 64-bit — a eviter',
  ],
}

// ── Function call convention ────────────────────────────────

export const FUNC_CONVENTION = {
  title: 'Convention d\'appel System V AMD64',
  args_int: ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'],
  args_float: ['XMM0', 'XMM1', 'XMM2', 'XMM3', 'XMM4', 'XMM5', 'XMM6', 'XMM7'],
  ret_int: 'RAX (128-bit: RDX:RAX)',
  ret_float: 'XMM0 (256-bit: XMM1:XMM0)',
  callerSaved: ['RAX', 'RCX', 'RDX', 'RSI', 'RDI', 'R8', 'R9', 'R10', 'R11', 'XMM0-XMM15'],
  calleeSaved: ['RBX', 'RBP', 'R12', 'R13', 'R14', 'R15'],
  stackAlign: '16 octets avant CALL (8 de retour addr → 16 apres CALL)',
  redZone: '128 octets sous RSP utilisables sans SUB RSP (leaf functions). Pas en kernel.',
  notes: [
    'Args supplementaires sur la stack (droite → gauche, comme C)',
    'L\'appelant nettoie la stack apres le retour',
    'Les fonctions variadiques (printf) : AL = nombre d\'args XMM utilises',
    'Les structures > 16 octets passees par pointeur (via RDI)',
  ],
}

// ── Stack frame layout ──────────────────────────────────────

export const STACK_LAYOUT = {
  title: 'Layout de la Stack Frame',
  diagram: [
    '    ┌─────────────────┐  haute adresse',
    '    │ ...args stack... │  [RBP+24], [RBP+16]  (7e arg+)',
    '    ├─────────────────┤',
    '    │  Return Address  │  [RBP+8]   (pousse par CALL)',
    '    ├─────────────────┤',
    '    │    Old RBP       │  [RBP]     (pousse par prologue)',
    '    ├─────────────────┤',
    '    │  Local var 1     │  [RBP-8]',
    '    │  Local var 2     │  [RBP-16]',
    '    │  ...             │',
    '    ├─────────────────┤',
    '    │  Red Zone (128B) │  [RSP-128] a [RSP] (leaf only)',
    '    └─────────────────┘  basse adresse (RSP)',
  ],
  prologue: [
    'push rbp          ; Sauvegarder le frame pointer',
    'mov  rbp, rsp     ; Nouveau frame pointer',
    'sub  rsp, N       ; Allouer N octets pour les locales',
  ],
  epilogue: [
    'leave             ; mov rsp,rbp + pop rbp',
    'ret               ; pop rip',
  ],
}

// ── NASM Directives ─────────────────────────────────────────

export interface DirectiveInfo {
  name: string
  syntax: string
  desc: string
}

export const NASM_DIRECTIVES: DirectiveInfo[] = [
  { name: 'section', syntax: 'section .text / .data / .bss / .rodata', desc: 'Declare une section ELF. .text=code, .data=donnees initialisees, .bss=donnees non-init, .rodata=constantes.' },
  { name: 'global', syntax: 'global _start', desc: 'Exporte un symbole pour le linker. _start = point d\'entree du programme.' },
  { name: 'extern', syntax: 'extern printf', desc: 'Declare un symbole externe (defini dans une autre lib). Necessite liaison avec libc.' },
  { name: 'db', syntax: 'msg db "Hello", 10, 0', desc: 'Define Byte(s). Chaque element = 1 octet. 10 = newline, 0 = null terminator.' },
  { name: 'dw', syntax: 'val dw 0x1234', desc: 'Define Word (2 octets, little-endian).' },
  { name: 'dd', syntax: 'val dd 42', desc: 'Define Doubleword (4 octets).' },
  { name: 'dq', syntax: 'val dq 0x123456789ABCDEF0', desc: 'Define Quadword (8 octets). Taille native en 64-bit.' },
  { name: 'resb', syntax: 'buffer resb 64', desc: 'Reserve Byte(s) non initialise(s). Section .bss uniquement.' },
  { name: 'resw', syntax: 'arr resw 10', desc: 'Reserve 10 words (20 octets).' },
  { name: 'resd', syntax: 'arr resd 5', desc: 'Reserve 5 doublewords (20 octets).' },
  { name: 'resq', syntax: 'arr resq 8', desc: 'Reserve 8 quadwords (64 octets).' },
  { name: 'equ', syntax: 'LEN equ $ - msg', desc: 'Constante symbolique. $ = adresse courante. LEN = taille de msg.' },
  { name: '%define', syntax: '%define BUFSIZE 1024', desc: 'Macro textuelle (comme #define en C).' },
  { name: '%macro', syntax: '%macro name nargs', desc: 'Debut de macro multi-ligne. %1, %2 = arguments.' },
  { name: '%endmacro', syntax: '%endmacro', desc: 'Fin de macro multi-ligne.' },
  { name: '%include', syntax: '%include "file.inc"', desc: 'Inclut un fichier source.' },
  { name: '%if', syntax: '%if expr / %elif / %else / %endif', desc: 'Assemblage conditionnel.' },
  { name: '%ifdef', syntax: '%ifdef SYMBOL', desc: 'Assemble si le symbole est defini.' },
  { name: '%rep', syntax: '%rep 10 / %endrep', desc: 'Repete un bloc N fois.' },
  { name: 'times', syntax: 'times 16 db 0', desc: 'Repete une instruction/directive N fois. times 510-($-$$) db 0 pour bootsector.' },
  { name: 'align', syntax: 'align 16', desc: 'Aligne a la prochaine frontiere de N octets (padding avec NOP).' },
  { name: 'bits', syntax: 'bits 64', desc: 'Mode d\'assemblage : 16, 32 ou 64 bits.' },
  { name: 'default', syntax: 'default rel', desc: 'Adressage relatif par defaut (necessaire pour PIE/shared libs).' },
  { name: 'struc', syntax: 'struc Name / .field resb N / endstruc', desc: 'Definition de structure. Acces: [instance + Name.field].' },
]

// ── Common patterns / idioms ────────────────────────────────

export interface PatternInfo {
  name: string
  code: string[]
  desc: string
}

export const ASM_PATTERNS: PatternInfo[] = [
  {
    name: 'Exit propre',
    code: ['mov rax, 60', 'xor rdi, rdi', 'syscall'],
    desc: 'sys_exit(0). xor rdi,rdi est plus court que mov rdi,0.',
  },
  {
    name: 'Write stdout',
    code: ['mov rax, 1', 'mov rdi, 1', 'mov rsi, msg', 'mov rdx, len', 'syscall'],
    desc: 'sys_write(1, msg, len). fd 1 = stdout, 2 = stderr.',
  },
  {
    name: 'Read stdin',
    code: ['mov rax, 0', 'mov rdi, 0', 'lea rsi, [buf]', 'mov rdx, 64', 'syscall'],
    desc: 'sys_read(0, buf, 64). Retourne le nombre d\'octets lus dans RAX.',
  },
  {
    name: 'Prologue de fonction',
    code: ['push rbp', 'mov rbp, rsp', 'sub rsp, 32'],
    desc: 'Sauvegarde RBP, cree une frame de 32 octets pour les variables locales.',
  },
  {
    name: 'Epilogue de fonction',
    code: ['leave', 'ret'],
    desc: 'Restaure RSP et RBP, retourne a l\'appelant.',
  },
  {
    name: 'Boucle comptee',
    code: ['mov rcx, 10', '.loop:', '    ; corps', '    dec rcx', '    jnz .loop'],
    desc: 'Boucle de 10 iterations. LOOP est plus lent que DEC+JNZ.',
  },
  {
    name: 'Mettre a zero',
    code: ['xor rax, rax'],
    desc: 'Plus rapide et plus court (2 octets) que mov rax, 0 (7 octets).',
  },
  {
    name: 'Test si zero',
    code: ['test rax, rax', 'jz .is_zero'],
    desc: 'Plus rapide que cmp rax, 0 (evite un encodage d\'immediat).',
  },
  {
    name: 'Swap sans temp',
    code: ['xchg rax, rbx'],
    desc: 'Echange atomique. Ou: xor a,b / xor b,a / xor a,b (sans lock bus).',
  },
  {
    name: 'Multiply par constante',
    code: ['lea rax, [rax + rax*4]  ; rax *= 5', 'shl rax, 3              ; rax *= 8'],
    desc: 'LEA + SHL plus rapide que IMUL pour les constantes simples.',
  },
  {
    name: 'Appel libc (printf)',
    code: ['section .data', '    fmt db "val = %d", 10, 0', 'section .text', '    extern printf', '    ; ...', '    lea rdi, [rel fmt]', '    mov rsi, 42', '    xor eax, eax  ; 0 args XMM', '    call printf'],
    desc: 'Appel C: RDI=format, RSI=arg1. AL=0 (pas d\'args float). Compiler avec gcc -no-pie.',
  },
  {
    name: 'Allocate on stack',
    code: ['sub rsp, 64    ; 64 octets', 'lea rdi, [rsp]  ; pointeur', '    ; utiliser...', 'add rsp, 64    ; liberer'],
    desc: 'Allocation locale sur la stack. Toujours realigner RSP a 16.',
  },
  {
    name: 'Execve /bin/sh',
    code: [
      'xor rdx, rdx         ; envp = NULL',
      'push rdx              ; null terminator',
      'mov rdi, 0x68732f6e69622f  ; "/bin/sh"',
      'push rdi',
      'mov rdi, rsp          ; path = rsp',
      'push rdx              ; argv[1] = NULL',
      'push rdi              ; argv[0] = path',
      'mov rsi, rsp          ; argv = rsp',
      'mov rax, 59           ; execve',
      'syscall',
    ],
    desc: 'Shellcode classique : execute /bin/sh. Utile en exploitation.',
  },
]
