/** Firmware analysis reference data */

export interface BinwalkOpt {
  flag: string
  desc: string
  cat: string
}

export interface MagicSignature {
  hex: string
  name: string
  desc: string
}

export const BINWALK_OPTS: BinwalkOpt[] = [
  // ── Scan ──────────────────────────────────
  { cat: 'Scan', flag: 'binwalk <file>', desc: 'Scan par defaut — identifie les signatures connues.' },
  { cat: 'Scan', flag: '-B / --signature', desc: 'Scan de signatures (defaut).' },
  { cat: 'Scan', flag: '-R / --raw=<str>', desc: 'Cherche un pattern brut (string ou hex).' },
  { cat: 'Scan', flag: '-A / --opcodes', desc: 'Scan d\'opcodes (detecte l\'architecture).' },
  { cat: 'Scan', flag: '-m / --magic=<f>', desc: 'Utilise un fichier magic personnalise.' },
  { cat: 'Scan', flag: '-b / --dumb', desc: 'Desactive les filtres intelligents.' },

  // ── Extract ───────────────────────────────
  { cat: 'Extract', flag: '-e / --extract', desc: 'Extrait les fichiers identifies automatiquement.' },
  { cat: 'Extract', flag: '-M / --matryoshka', desc: 'Extraction recursive (firmware dans firmware).' },
  { cat: 'Extract', flag: '-d / --depth=<N>', desc: 'Profondeur max d\'extraction recursive.' },
  { cat: 'Extract', flag: '-C / --directory=<dir>', desc: 'Repertoire de sortie pour l\'extraction.' },
  { cat: 'Extract', flag: '-j / --size=<N>', desc: 'Taille max des fichiers extraits.' },
  { cat: 'Extract', flag: '-n / --count=<N>', desc: 'Nombre max de resultats.' },
  { cat: 'Extract', flag: '--run-as=<user>', desc: 'Execute les commandes d\'extraction avec cet utilisateur.' },
  { cat: 'Extract', flag: '-D / --dd=<type:ext:cmd>', desc: 'Extraction personnalisee: type regex, extension, commande.' },

  // ── Entropy ───────────────────────────────
  { cat: 'Entropy', flag: '-E / --entropy', desc: 'Analyse d\'entropie (detecte compression/chiffrement).' },
  { cat: 'Entropy', flag: '-F / --fast', desc: 'Entropie rapide (moins de precision).' },
  { cat: 'Entropy', flag: '-J / --save', desc: 'Sauvegarde le graphe d\'entropie en PNG.' },
  { cat: 'Entropy', flag: '-Q / --nlegend', desc: 'Sans legende sur le graphe.' },
  { cat: 'Entropy', flag: '-N / --nplot', desc: 'Pas de graphe, juste les donnees.' },
  { cat: 'Entropy', flag: '-H / --high=<val>', desc: 'Seuil d\'entropie haute (defaut: 0.95).' },
  { cat: 'Entropy', flag: '-L / --low=<val>', desc: 'Seuil d\'entropie basse (defaut: 0.85).' },

  // ── Other ─────────────────────────────────
  { cat: 'Other', flag: '-W / --hexdump', desc: 'Hexdump du fichier.' },
  { cat: 'Other', flag: '-w / --string', desc: 'Cherche des strings imprimables.' },
  { cat: 'Other', flag: '-l / --length=<N>', desc: 'Taille min des strings.' },
  { cat: 'Other', flag: '-o / --offset=<N>', desc: 'Offset de debut du scan.' },
  { cat: 'Other', flag: '-t / --term', desc: 'Format le output pour le terminal.' },
  { cat: 'Other', flag: '--log=<file>', desc: 'Log les resultats dans un fichier.' },
]

export const BINWALK_CATS = ['Tout', 'Scan', 'Extract', 'Entropy', 'Other']

export const MAGIC_SIGNATURES: MagicSignature[] = [
  { hex: '7F 45 4C 46', name: 'ELF', desc: 'Executable Linux/Unix (binaire ELF).' },
  { hex: '4D 5A', name: 'PE/MZ', desc: 'Executable Windows (PE).' },
  { hex: 'CA FE BA BE', name: 'Mach-O (FAT)', desc: 'Executable macOS universal binary.' },
  { hex: 'FE ED FA CE/CF', name: 'Mach-O', desc: 'Executable macOS 32/64-bit.' },
  { hex: '50 4B 03 04', name: 'ZIP/APK/JAR', desc: 'Archive ZIP (aussi APK Android, JAR Java).' },
  { hex: '1F 8B 08', name: 'gzip', desc: 'Donnees compressees gzip.' },
  { hex: '42 5A 68', name: 'bzip2', desc: 'Donnees compressees bzip2.' },
  { hex: 'FD 37 7A 58 5A', name: 'xz', desc: 'Donnees compressees xz/LZMA2.' },
  { hex: '5D 00 00', name: 'LZMA', desc: 'Donnees compressees LZMA.' },
  { hex: '68 73 71 73', name: 'SquashFS', desc: 'Filesystem compresse (courant dans les firmwares).' },
  { hex: '73 71 73 68', name: 'SquashFS (BE)', desc: 'SquashFS big-endian.' },
  { hex: '85 19 01 E0', name: 'JFFS2 (LE)', desc: 'Journalling Flash File System v2 (little-endian).' },
  { hex: 'E0 01 19 85', name: 'JFFS2 (BE)', desc: 'JFFS2 big-endian.' },
  { hex: '55 42 49 23', name: 'UBI', desc: 'Unsorted Block Images (flash NAND).' },
  { hex: '27 05 19 56', name: 'uImage', desc: 'U-Boot image header.' },
  { hex: 'D0 0D FE ED', name: 'FDT/DTB', desc: 'Flattened Device Tree (Device Tree Blob).' },
  { hex: '30 37 30 37', name: 'CPIO', desc: 'Archive CPIO (initramfs Linux).' },
  { hex: '89 50 4E 47', name: 'PNG', desc: 'Image PNG.' },
  { hex: 'FF D8 FF', name: 'JPEG', desc: 'Image JPEG.' },
  { hex: '1F 9D', name: 'compress', desc: 'Unix compress (.Z).' },
  { hex: '4352 414D', name: 'CramFS', desc: 'Compressed ROM filesystem.' },
  { hex: 'EB 3C 90', name: 'FAT Boot', desc: 'Boot sector FAT12/16.' },
  { hex: '53 EF', name: 'ext2/3/4', desc: 'Superblock ext (a offset 0x438).' },
]

export const ENTROPY_GUIDE = [
  { range: '0.0 — 0.2', meaning: 'Donnees tres uniformes (padding, zeros, repetitions).' },
  { range: '0.2 — 0.5', meaning: 'Texte / code non-compresse. Strings ASCII, assembleur.' },
  { range: '0.5 — 0.7', meaning: 'Code compile, donnees structurees.' },
  { range: '0.7 — 0.9', meaning: 'Donnees compressees (gzip, LZMA, SquashFS).' },
  { range: '0.9 — 1.0', meaning: 'Chiffrement ou tres haute compression. Probablement AES/random.' },
]

export const FW_PATTERNS = [
  {
    name: 'Extraction basique',
    desc: 'Extraire et analyser le contenu d\'un firmware.',
    code: [
      'binwalk firmware.bin              # scanner',
      'binwalk -e firmware.bin           # extraire',
      'binwalk -Me firmware.bin          # extraction recursive',
      'cd _firmware.bin.extracted/',
      'find . -name "*.conf" -o -name "passwd" -o -name "*.key"',
    ],
  },
  {
    name: 'Analyse d\'entropie',
    desc: 'Detecter les zones compressees/chiffrees.',
    code: [
      'binwalk -E firmware.bin           # graphe d\'entropie',
      '# Entropie > 0.9 → probablement chiffre',
      '# Entropie 0.7-0.9 → probablement compresse',
      '# Entropie < 0.5 → code/donnees en clair',
    ],
  },
  {
    name: 'Chercher des secrets',
    desc: 'Trouver des credentials et cles dans un firmware extrait.',
    code: [
      'grep -r "password" ./',
      'grep -r "admin" ./',
      'find . -name "shadow" -o -name "passwd"',
      'find . -name "*.pem" -o -name "*.key" -o -name "*.crt"',
      'strings firmware.bin | grep -i "api_key\\|secret\\|token"',
    ],
  },
  {
    name: 'Identifier l\'architecture',
    desc: 'Determiner le CPU cible du firmware.',
    code: [
      'binwalk -A firmware.bin           # scan opcodes',
      'file extracted_binary             # info ELF',
      'readelf -h extracted_binary       # headers ELF',
      '# Architectures courantes:',
      '# ARM (routeurs, IoT), MIPS (routeurs anciens),',
      '# x86 (appliances), PPC (equipements reseau)',
    ],
  },
]
