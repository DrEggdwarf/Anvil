/** Debug mode (GDB/pwndbg) reference data */

export interface GdbCmd {
  cmd: string
  shortcut: string
  args: string
  desc: string
  cat: string
}

export const GDB_CMDS: GdbCmd[] = [
  // ── Execution ─────────────────────────────
  { cat: 'Execution', cmd: 'run', shortcut: 'r', args: '[args]', desc: 'Lance le programme avec les arguments.' },
  { cat: 'Execution', cmd: 'start', shortcut: '', args: '[args]', desc: 'Lance et s\'arrete au debut de main().' },
  { cat: 'Execution', cmd: 'continue', shortcut: 'c', args: '', desc: 'Continue l\'execution jusqu\'au prochain breakpoint.' },
  { cat: 'Execution', cmd: 'next', shortcut: 'n', args: '', desc: 'Step over — execute une ligne (ne rentre pas dans les fonctions).' },
  { cat: 'Execution', cmd: 'step', shortcut: 's', args: '', desc: 'Step into — entre dans les fonctions.' },
  { cat: 'Execution', cmd: 'nexti', shortcut: 'ni', args: '', desc: 'Step over une instruction assembleur.' },
  { cat: 'Execution', cmd: 'stepi', shortcut: 'si', args: '', desc: 'Step into une instruction assembleur.' },
  { cat: 'Execution', cmd: 'finish', shortcut: 'fin', args: '', desc: 'Execute jusqu\'au retour de la fonction courante.' },
  { cat: 'Execution', cmd: 'until', shortcut: 'u', args: '<loc>', desc: 'Continue jusqu\'a la ligne/adresse specifiee.' },
  { cat: 'Execution', cmd: 'kill', shortcut: 'k', args: '', desc: 'Tue le programme en cours de debug.' },
  { cat: 'Execution', cmd: 'set args', shortcut: '', args: '<args>', desc: 'Definit les arguments pour le prochain run.' },

  // ── Breakpoints ───────────────────────────
  { cat: 'Breakpoints', cmd: 'break', shortcut: 'b', args: '<loc>', desc: 'Breakpoint a l\'adresse, fonction, ou ligne.' },
  { cat: 'Breakpoints', cmd: 'break *', shortcut: 'b *', args: '<addr>', desc: 'Breakpoint a une adresse exacte.' },
  { cat: 'Breakpoints', cmd: 'break if', shortcut: '', args: '<loc> if <expr>', desc: 'Breakpoint conditionnel.' },
  { cat: 'Breakpoints', cmd: 'tbreak', shortcut: 'tb', args: '<loc>', desc: 'Breakpoint temporaire (supprime apres 1 hit).' },
  { cat: 'Breakpoints', cmd: 'watch', shortcut: '', args: '<expr>', desc: 'Watchpoint — arrete quand la valeur change.' },
  { cat: 'Breakpoints', cmd: 'rwatch', shortcut: '', args: '<expr>', desc: 'Read watchpoint — arrete a la lecture.' },
  { cat: 'Breakpoints', cmd: 'catch', shortcut: '', args: '<event>', desc: 'Catch syscall, signal, throw, fork...' },
  { cat: 'Breakpoints', cmd: 'info breakpoints', shortcut: 'i b', args: '', desc: 'Liste tous les breakpoints.' },
  { cat: 'Breakpoints', cmd: 'delete', shortcut: 'd', args: '<N>', desc: 'Supprime le breakpoint N.' },
  { cat: 'Breakpoints', cmd: 'disable/enable', shortcut: '', args: '<N>', desc: 'Active/desactive un breakpoint.' },
  { cat: 'Breakpoints', cmd: 'commands', shortcut: '', args: '<N>', desc: 'Commandes auto a executer quand le BP est touche.' },

  // ── Info / Registers ──────────────────────
  { cat: 'Registers', cmd: 'info registers', shortcut: 'i r', args: '', desc: 'Affiche tous les registres generaux.' },
  { cat: 'Registers', cmd: 'info registers', shortcut: 'i r', args: '<reg>', desc: 'Affiche un registre specifique.' },
  { cat: 'Registers', cmd: 'info all-registers', shortcut: '', args: '', desc: 'Tous les registres (inclut SSE, flags...).' },
  { cat: 'Registers', cmd: 'set $rax', shortcut: '', args: '= <val>', desc: 'Modifie un registre.' },
  { cat: 'Registers', cmd: 'print $rsp', shortcut: 'p', args: '', desc: 'Affiche la valeur d\'un registre.' },
  { cat: 'Registers', cmd: 'print/x', shortcut: 'p/x', args: '<expr>', desc: 'Affiche en hex. /d=dec, /t=bin, /o=oct.' },

  // ── Memory ────────────────────────────────
  { cat: 'Memory', cmd: 'x/', shortcut: '', args: '<N><f><u> <addr>', desc: 'Examine memoire. N=count, f=format, u=unit.' },
  { cat: 'Memory', cmd: 'x/10gx $rsp', shortcut: '', args: '', desc: 'Stack: 10 quadwords hex.' },
  { cat: 'Memory', cmd: 'x/20i $rip', shortcut: '', args: '', desc: 'Desassemble 20 instructions depuis RIP.' },
  { cat: 'Memory', cmd: 'x/s', shortcut: '', args: '<addr>', desc: 'Affiche la string a l\'adresse.' },
  { cat: 'Memory', cmd: 'x/bx', shortcut: '', args: '<addr>', desc: 'Octets bruts en hex.' },
  { cat: 'Memory', cmd: 'set {int}', shortcut: '', args: '<addr> = <val>', desc: 'Ecrit en memoire.' },
  { cat: 'Memory', cmd: 'find', shortcut: '', args: '<start>, <end>, <val>', desc: 'Cherche une valeur en memoire.' },
  { cat: 'Memory', cmd: 'info proc mappings', shortcut: '', args: '', desc: 'Carte memoire du processus (sections, permissions).' },

  // ── Stack ─────────────────────────────────
  { cat: 'Stack', cmd: 'backtrace', shortcut: 'bt', args: '', desc: 'Trace de la pile d\'appels (callstack).' },
  { cat: 'Stack', cmd: 'frame', shortcut: 'f', args: '<N>', desc: 'Selectionne le frame N.' },
  { cat: 'Stack', cmd: 'up/down', shortcut: '', args: '', desc: 'Monte/descend d\'un frame dans la callstack.' },
  { cat: 'Stack', cmd: 'info frame', shortcut: '', args: '', desc: 'Details du frame courant (saved RIP, RBP...).' },
  { cat: 'Stack', cmd: 'info locals', shortcut: '', args: '', desc: 'Variables locales du frame courant.' },
  { cat: 'Stack', cmd: 'info args', shortcut: '', args: '', desc: 'Arguments de la fonction courante.' },

  // ── Disassembly ───────────────────────────
  { cat: 'Disasm', cmd: 'disassemble', shortcut: 'disas', args: '<func>', desc: 'Desassemble une fonction.' },
  { cat: 'Disasm', cmd: 'set disassembly-flavor', shortcut: '', args: '<intel|att>', desc: 'Syntaxe Intel ou AT&T.' },
  { cat: 'Disasm', cmd: 'layout asm', shortcut: '', args: '', desc: 'Mode TUI assembleur.' },
  { cat: 'Disasm', cmd: 'layout split', shortcut: '', args: '', desc: 'Mode TUI source + assembleur.' },

  // ── Signals ───────────────────────────────
  { cat: 'Signals', cmd: 'handle', shortcut: '', args: '<sig> <action>', desc: 'Configure la gestion d\'un signal (stop/nostop, pass/nopass).' },
  { cat: 'Signals', cmd: 'signal', shortcut: '', args: '<sig>', desc: 'Envoie un signal au programme.' },
  { cat: 'Signals', cmd: 'info signals', shortcut: '', args: '', desc: 'Liste la config de gestion de chaque signal.' },
]

export const GDB_CATS = ['Tout', 'Execution', 'Breakpoints', 'Registers', 'Memory', 'Stack', 'Disasm', 'Signals']

export const PWNDBG_CMDS = [
  { cmd: 'context', desc: 'Affiche les registres, stack, code, backtrace (auto a chaque stop).' },
  { cmd: 'vmmap', desc: 'Carte memoire avec permissions (comme /proc/pid/maps).' },
  { cmd: 'telescope', desc: 'Dereference la stack en profondeur (suit les pointeurs).' },
  { cmd: 'search', desc: 'Cherche des patterns en memoire (string, int, bytes).' },
  { cmd: 'heap', desc: 'Affiche les chunks du heap (ptmalloc2).' },
  { cmd: 'bins', desc: 'Affiche les freelists du heap (tcache, fastbin, unsorted...).' },
  { cmd: 'vis_heap_chunks', desc: 'Visualisation graphique des chunks du heap.' },
  { cmd: 'cyclic', desc: 'Genere/trouve des patterns De Bruijn (offset finding).' },
  { cmd: 'rop', desc: 'Cherche des gadgets ROP dans le binaire.' },
  { cmd: 'got', desc: 'Affiche la GOT avec les adresses resolues.' },
  { cmd: 'plt', desc: 'Affiche la PLT.' },
  { cmd: 'checksec', desc: 'Protections du binaire (NX, ASLR, canary, PIE, RELRO).' },
  { cmd: 'canary', desc: 'Affiche la valeur du stack canary.' },
  { cmd: 'retaddr', desc: 'Affiche les return addresses sur la stack.' },
  { cmd: 'elfheader', desc: 'Headers ELF du binaire charge.' },
  { cmd: 'nextret', desc: 'Continue jusqu\'a la prochaine instruction RET.' },
  { cmd: 'nextcall', desc: 'Continue jusqu\'au prochain CALL.' },
  { cmd: 'nextsyscall', desc: 'Continue jusqu\'au prochain SYSCALL.' },
  { cmd: 'procinfo', desc: 'Infos detaillees sur le processus (/proc/pid/).' },
  { cmd: 'xinfo', desc: 'Infos sur une adresse (section, permissions, mapping).' },
  { cmd: 'distance', desc: 'Calcule la distance entre deux adresses.' },
  { cmd: 'dumpargs', desc: 'Affiche les arguments d\'un appel de fonction.' },
  { cmd: 'regs', desc: 'Registres avec coloration et dereferencing.' },
  { cmd: 'stack', desc: 'Stack avec telescope et annotations.' },
]

export const GDB_EXAMINE_FORMATS = {
  title: 'x/<count><format><size> <addr>',
  formats: [
    { code: 'x', desc: 'Hexadecimal' },
    { code: 'd', desc: 'Decimal signe' },
    { code: 'u', desc: 'Decimal non-signe' },
    { code: 'o', desc: 'Octal' },
    { code: 't', desc: 'Binaire' },
    { code: 'a', desc: 'Adresse (symbole)' },
    { code: 'c', desc: 'Caractere' },
    { code: 's', desc: 'String' },
    { code: 'i', desc: 'Instruction ASM' },
    { code: 'f', desc: 'Float' },
  ],
  sizes: [
    { code: 'b', desc: 'Byte (1 octet)' },
    { code: 'h', desc: 'Halfword (2 octets)' },
    { code: 'w', desc: 'Word (4 octets)' },
    { code: 'g', desc: 'Giant (8 octets)' },
  ],
  examples: [
    'x/20gx $rsp      — 20 quadwords hex (stack)',
    'x/10i $rip       — 10 instructions depuis RIP',
    'x/s 0x404000      — string a l\'adresse',
    'x/40bx $rsp      — 40 octets hex (stack brut)',
    'x/4wx $rbp-0x10  — 4 words a rbp-16 (variables locales)',
  ],
}
