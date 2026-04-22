/** Reverse Engineering (rizin) reference data */

export interface RizinCmd {
  cmd: string
  args: string
  desc: string
  cat: string
}

export interface BinaryFormatInfo {
  name: string
  fields: { field: string; offset: string; size: string; desc: string }[]
}

export const RIZIN_CMDS: RizinCmd[] = [
  // ── Analysis ──────────────────────────────
  { cat: 'Analysis', cmd: 'aaa', args: '', desc: 'Analyse complete (fonctions, refs, strings, types).' },
  { cat: 'Analysis', cmd: 'aa', args: '', desc: 'Analyse basique des fonctions.' },
  { cat: 'Analysis', cmd: 'afl', args: '', desc: 'Liste toutes les fonctions detectees.' },
  { cat: 'Analysis', cmd: 'afn', args: '<name> [addr]', desc: 'Renomme une fonction.' },
  { cat: 'Analysis', cmd: 'afi', args: '[addr]', desc: 'Infos detaillees sur la fonction a l\'adresse.' },
  { cat: 'Analysis', cmd: 'axt', args: '<addr>', desc: 'Cross-references vers l\'adresse (qui appelle/reference).' },
  { cat: 'Analysis', cmd: 'axf', args: '<addr>', desc: 'Cross-references depuis l\'adresse (qu\'est-ce qui est appele).' },
  { cat: 'Analysis', cmd: 'agC', args: '', desc: 'Callgraph global en ASCII.' },
  { cat: 'Analysis', cmd: 'agf', args: '', desc: 'Graphe de flot de la fonction courante.' },
  { cat: 'Analysis', cmd: 'afb', args: '', desc: 'Liste les basic blocks de la fonction courante.' },
  { cat: 'Analysis', cmd: 'afv', args: '', desc: 'Variables locales de la fonction courante.' },
  { cat: 'Analysis', cmd: 'aar', args: '', desc: 'Analyse les references (data, strings).' },

  // ── Disassembly ───────────────────────────
  { cat: 'Disasm', cmd: 'pd', args: '<N>', desc: 'Desassemble N instructions depuis l\'adresse courante.' },
  { cat: 'Disasm', cmd: 'pdf', args: '', desc: 'Desassemble la fonction entiere.' },
  { cat: 'Disasm', cmd: 'pD', args: '<N>', desc: 'Desassemble N octets.' },
  { cat: 'Disasm', cmd: 'pdj', args: '<N>', desc: 'Desassemble en JSON.' },
  { cat: 'Disasm', cmd: 'pdc', args: '', desc: 'Pseudo-decompilation de la fonction courante.' },
  { cat: 'Disasm', cmd: 'pdg', args: '', desc: 'Decompilation via Ghidra plugin (si disponible).' },

  // ── Info ───────────────────────────────────
  { cat: 'Info', cmd: 'i', args: '', desc: 'Infos generales du binaire (format, arch, bits, endian).' },
  { cat: 'Info', cmd: 'ie', args: '', desc: 'Point d\'entree (entrypoint).' },
  { cat: 'Info', cmd: 'iS', args: '', desc: 'Sections du binaire.' },
  { cat: 'Info', cmd: 'iSS', args: '', desc: 'Segments du binaire.' },
  { cat: 'Info', cmd: 'ii', args: '', desc: 'Imports (fonctions importees).' },
  { cat: 'Info', cmd: 'iE', args: '', desc: 'Exports (symboles exportes).' },
  { cat: 'Info', cmd: 'is', args: '', desc: 'Symboles.' },
  { cat: 'Info', cmd: 'iz', args: '', desc: 'Strings dans les sections data.' },
  { cat: 'Info', cmd: 'izz', args: '', desc: 'Strings dans tout le binaire.' },
  { cat: 'Info', cmd: 'il', args: '', desc: 'Libraries liees (dependances).' },
  { cat: 'Info', cmd: 'iR', args: '', desc: 'Relocations.' },
  { cat: 'Info', cmd: 'iH', args: '', desc: 'Headers du binaire.' },
  { cat: 'Info', cmd: 'ic', args: '', desc: 'Classes (C++/Java/ObjC).' },

  // ── Navigation ────────────────────────────
  { cat: 'Navigation', cmd: 's', args: '<addr|sym>', desc: 'Seek — deplace le curseur a l\'adresse ou symbole.' },
  { cat: 'Navigation', cmd: 's+', args: '<N>', desc: 'Avance de N octets.' },
  { cat: 'Navigation', cmd: 's-', args: '<N>', desc: 'Recule de N octets.' },
  { cat: 'Navigation', cmd: 's main', args: '', desc: 'Va au symbole main.' },
  { cat: 'Navigation', cmd: 'sf', args: '', desc: 'Seek au debut de la fonction suivante.' },

  // ── Print / Memory ────────────────────────
  { cat: 'Print', cmd: 'px', args: '<N>', desc: 'Hexdump de N octets.' },
  { cat: 'Print', cmd: 'pxw', args: '<N>', desc: 'Hexdump en words (4 octets).' },
  { cat: 'Print', cmd: 'pxq', args: '<N>', desc: 'Hexdump en quadwords (8 octets).' },
  { cat: 'Print', cmd: 'ps', args: '', desc: 'Print string a l\'adresse courante.' },
  { cat: 'Print', cmd: 'p8', args: '<N>', desc: 'Print N octets en hex brut.' },
  { cat: 'Print', cmd: 'pf', args: '<fmt>', desc: 'Print formatte (struct, type...).' },

  // ── Search ────────────────────────────────
  { cat: 'Search', cmd: '/', args: '<string>', desc: 'Cherche une chaine dans le binaire.' },
  { cat: 'Search', cmd: '/x', args: '<hex>', desc: 'Cherche un pattern hex.' },
  { cat: 'Search', cmd: '/R', args: '<opcode>', desc: 'Cherche des ROP gadgets.' },
  { cat: 'Search', cmd: '/r', args: '<addr>', desc: 'Cherche les references a l\'adresse.' },
  { cat: 'Search', cmd: '/a', args: '<asm>', desc: 'Cherche une instruction assembleur.' },
  { cat: 'Search', cmd: '/c', args: '<opcode>', desc: 'Cherche des appels (call) a la fonction.' },

  // ── Write / Patch ─────────────────────────
  { cat: 'Patch', cmd: 'w', args: '<string>', desc: 'Ecrit une chaine a l\'adresse courante.' },
  { cat: 'Patch', cmd: 'wx', args: '<hex>', desc: 'Ecrit des octets hex.' },
  { cat: 'Patch', cmd: 'wa', args: '<asm>', desc: 'Assemble et ecrit l\'instruction.' },
  { cat: 'Patch', cmd: 'wao', args: '<op>', desc: 'Patch operation (nop, jz→jnz, etc.).' },
  { cat: 'Patch', cmd: 'wc', args: '', desc: 'Liste les modifications (cache des patches).' },

  // ── Flags / Comments ──────────────────────
  { cat: 'Flags', cmd: 'f', args: '<name> [addr]', desc: 'Cree un flag (label) a l\'adresse.' },
  { cat: 'Flags', cmd: 'f-', args: '<name>', desc: 'Supprime un flag.' },
  { cat: 'Flags', cmd: 'fl', args: '', desc: 'Liste tous les flags.' },
  { cat: 'Flags', cmd: 'CC', args: '<text>', desc: 'Ajoute un commentaire a l\'adresse courante.' },
  { cat: 'Flags', cmd: 'CCf', args: '', desc: 'Commentaire de fonction.' },

  // ── Visual ────────────────────────────────
  { cat: 'Visual', cmd: 'V', args: '', desc: 'Mode visuel hex.' },
  { cat: 'Visual', cmd: 'VV', args: '', desc: 'Mode graphe visuel.' },
  { cat: 'Visual', cmd: 'v', args: '', desc: 'Panels (TUI multi-vues).' },
]

export const RIZIN_CATS = ['Tout', 'Analysis', 'Disasm', 'Info', 'Navigation', 'Print', 'Search', 'Patch', 'Flags', 'Visual']

export const ELF_FORMAT: BinaryFormatInfo = {
  name: 'ELF Header',
  fields: [
    { field: 'e_ident[0..3]', offset: '0x00', size: '4', desc: 'Magic: 0x7f ELF' },
    { field: 'e_ident[4]', offset: '0x04', size: '1', desc: 'Classe: 1=32-bit, 2=64-bit' },
    { field: 'e_ident[5]', offset: '0x05', size: '1', desc: 'Endianness: 1=LE, 2=BE' },
    { field: 'e_type', offset: '0x10', size: '2', desc: 'Type: 1=REL, 2=EXEC, 3=DYN(PIE/SO), 4=CORE' },
    { field: 'e_machine', offset: '0x12', size: '2', desc: 'Arch: 0x3E=x86-64, 0x03=x86, 0xB7=AArch64' },
    { field: 'e_entry', offset: '0x18', size: '8', desc: 'Point d\'entree (adresse virtuelle).' },
    { field: 'e_phoff', offset: '0x20', size: '8', desc: 'Offset table des Program Headers.' },
    { field: 'e_shoff', offset: '0x28', size: '8', desc: 'Offset table des Section Headers.' },
    { field: 'e_phnum', offset: '0x38', size: '2', desc: 'Nombre de Program Headers.' },
    { field: 'e_shnum', offset: '0x3C', size: '2', desc: 'Nombre de Section Headers.' },
  ],
}

export const ELF_SECTIONS = [
  { name: '.text', desc: 'Code executable. Permissions R-X.' },
  { name: '.data', desc: 'Donnees initialisees (variables globales). R/W.' },
  { name: '.bss', desc: 'Donnees non-initialisees (zeroes au runtime). R/W.' },
  { name: '.rodata', desc: 'Constantes en lecture seule. R--.' },
  { name: '.plt', desc: 'Procedure Linkage Table — stubs pour appels dynamiques.' },
  { name: '.got', desc: 'Global Offset Table — adresses resolues par le linker dynamique.' },
  { name: '.got.plt', desc: 'GOT entries pour la PLT (lazy binding).' },
  { name: '.dynamic', desc: 'Info pour le linker dynamique (DT_NEEDED, etc.).' },
  { name: '.dynsym', desc: 'Symboles dynamiques (imports/exports).' },
  { name: '.dynstr', desc: 'Table de strings pour les symboles dynamiques.' },
  { name: '.rel/.rela', desc: 'Tables de relocation.' },
  { name: '.init/.fini', desc: 'Code d\'initialisation/finalisation.' },
  { name: '.init_array', desc: 'Pointeurs de fonctions executees avant main().' },
  { name: '.fini_array', desc: 'Pointeurs de fonctions executees apres exit().' },
  { name: '.note', desc: 'Metadonnees (build-id, ABI version).' },
  { name: '.eh_frame', desc: 'Info de deroulement de stack (exceptions, DWARF).' },
  { name: '.symtab', desc: 'Table de symboles complete (strip supprime).' },
  { name: '.strtab', desc: 'Table de strings pour .symtab.' },
  { name: '.comment', desc: 'Commentaire compilateur (GCC version etc.).' },
  { name: '.debug_*', desc: 'Sections DWARF (info de debug, -g).' },
]

export const RE_PATTERNS = [
  {
    name: 'Identifier la protection',
    desc: 'Commandes checksec equivalentes dans rizin.',
    code: ['iI            ; infos binaire (canary, nx, pic, relro)', 'iS            ; sections + permissions', 'rabin2 -I <f> ; depuis le shell'],
  },
  {
    name: 'Trouver main()',
    desc: 'Localiser le point d\'entree et main dans un binaire stripped.',
    code: ['ie            ; entrypoint', 'aaa           ; analyse complete', 'afl~main      ; chercher main dans la liste', 's main        ; aller a main', 'pdf           ; desassembler main'],
  },
  {
    name: 'Tracer les appels',
    desc: 'Suivre le flot d\'execution et les cross-references.',
    code: ['axt @sym.func ; qui appelle func ?', 'axf @sym.func ; que fait func ?', 'agCd          ; callgraph DOT (graphviz)', 'VV            ; mode graphe interactif'],
  },
  {
    name: 'Chercher des vulns',
    desc: 'Patterns courants a chercher dans un binaire.',
    code: ['/R pop rdi    ; gadgets ROP', '/c sym.imp.gets ; appels a gets() (vuln)', '/c sym.imp.strcpy ; appels a strcpy()', 'afl~str       ; fonctions liees aux strings', 'iz~password   ; strings sensibles'],
  },
  {
    name: 'Patcher un binaire',
    desc: 'Modifier des instructions pour bypasser des checks.',
    code: ['s 0x401234    ; aller a l\'adresse', 'pd 5          ; voir les instructions', 'wao nop       ; remplacer par NOP', 'wao jz        ; inverser un jump conditionnel', 'wc            ; voir les modifications', 'r2 -w file    ; ouvrir en ecriture'],
  },
]
