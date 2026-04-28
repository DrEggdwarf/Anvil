/** ICS/OT Protocols reference data */

export interface ModbusFunc {
  code: number
  name: string
  access: string
  desc: string
}

export interface ModbusRegType {
  type: string
  address: string
  access: string
  size: string
  desc: string
}

export interface ModbusException {
  code: number
  name: string
  desc: string
}

export const MODBUS_FUNCTIONS: ModbusFunc[] = [
  // ── Read ──────────────────────────────────
  { code: 0x01, name: 'Read Coils', access: 'R', desc: 'Lit l\'etat de N coils (sorties discretes, 1 bit).' },
  { code: 0x02, name: 'Read Discrete Inputs', access: 'R', desc: 'Lit N entrees discretes (1 bit, lecture seule).' },
  { code: 0x03, name: 'Read Holding Registers', access: 'R', desc: 'Lit N registres de maintien (16 bits, R/W).' },
  { code: 0x04, name: 'Read Input Registers', access: 'R', desc: 'Lit N registres d\'entree (16 bits, lecture seule).' },

  // ── Write Single ──────────────────────────
  { code: 0x05, name: 'Write Single Coil', access: 'W', desc: 'Ecrit un coil. Valeur: 0xFF00=ON, 0x0000=OFF.' },
  { code: 0x06, name: 'Write Single Register', access: 'W', desc: 'Ecrit un registre de maintien (16 bits).' },

  // ── Write Multiple ────────────────────────
  { code: 0x0F, name: 'Write Multiple Coils', access: 'W', desc: 'Ecrit N coils d\'un coup.' },
  { code: 0x10, name: 'Write Multiple Registers', access: 'W', desc: 'Ecrit N registres d\'un coup.' },

  // ── Diagnostics ───────────────────────────
  { code: 0x07, name: 'Read Exception Status', access: 'R', desc: 'Lit 8 bits de statut d\'exception.' },
  { code: 0x08, name: 'Diagnostics', access: 'R/W', desc: 'Tests de diagnostic (loopback, compteurs, etc.).' },
  { code: 0x0B, name: 'Get Comm Event Counter', access: 'R', desc: 'Compteur d\'evenements de communication.' },
  { code: 0x0C, name: 'Get Comm Event Log', access: 'R', desc: 'Journal des evenements de communication.' },
  { code: 0x11, name: 'Report Server ID', access: 'R', desc: 'Identification de l\'appareil (vendor, product).' },
  { code: 0x2B, name: 'Read Device Identification', access: 'R', desc: 'Identification MEI — vendor, product, version.' },

  // ── File / FIFO ───────────────────────────
  { code: 0x14, name: 'Read File Record', access: 'R', desc: 'Lit un enregistrement de fichier.' },
  { code: 0x15, name: 'Write File Record', access: 'W', desc: 'Ecrit un enregistrement de fichier.' },
  { code: 0x16, name: 'Mask Write Register', access: 'W', desc: 'Ecriture masquee AND/OR sur un registre.' },
  { code: 0x17, name: 'Read/Write Multiple Regs', access: 'R/W', desc: 'Lecture et ecriture atomique de registres.' },
  { code: 0x18, name: 'Read FIFO Queue', access: 'R', desc: 'Lit le contenu d\'une file FIFO.' },
]

export const MODBUS_REG_TYPES: ModbusRegType[] = [
  { type: 'Coil', address: '0xxxx (0-65535)', access: 'R/W', size: '1 bit', desc: 'Sortie discrete. ON/OFF. Actionneur (relais, vanne).' },
  { type: 'Discrete Input', address: '1xxxx', access: 'R', size: '1 bit', desc: 'Entree discrete. Capteur tout-ou-rien (switch, detecteur).' },
  { type: 'Input Register', address: '3xxxx', access: 'R', size: '16 bits', desc: 'Registre d\'entree. Mesure analogique (temperature, pression).' },
  { type: 'Holding Register', address: '4xxxx', access: 'R/W', size: '16 bits', desc: 'Registre de maintien. Configuration, setpoints, commandes.' },
]

export const MODBUS_EXCEPTIONS: ModbusException[] = [
  { code: 0x01, name: 'Illegal Function', desc: 'Code fonction non supporte par l\'esclave.' },
  { code: 0x02, name: 'Illegal Data Address', desc: 'Adresse de registre invalide.' },
  { code: 0x03, name: 'Illegal Data Value', desc: 'Valeur hors plage autorisee.' },
  { code: 0x04, name: 'Server Device Failure', desc: 'Erreur interne de l\'appareil.' },
  { code: 0x05, name: 'Acknowledge', desc: 'Requete acceptee mais traitement long en cours.' },
  { code: 0x06, name: 'Server Device Busy', desc: 'Appareil occupe, reessayer plus tard.' },
  { code: 0x08, name: 'Memory Parity Error', desc: 'Erreur de parite memoire.' },
  { code: 0x0A, name: 'Gateway Path Unavailable', desc: 'Passerelle: chemin indisponible.' },
  { code: 0x0B, name: 'Gateway Target Failed', desc: 'Passerelle: appareil cible ne repond pas.' },
]

export const MODBUS_FRAME = {
  tcp: {
    name: 'Modbus TCP (MBAP Header)',
    fields: [
      { field: 'Transaction ID', size: '2', desc: 'Identifiant de la requete (client choisit).' },
      { field: 'Protocol ID', size: '2', desc: 'Toujours 0x0000 pour Modbus.' },
      { field: 'Length', size: '2', desc: 'Nombre d\'octets suivants (Unit ID + PDU).' },
      { field: 'Unit ID', size: '1', desc: 'Adresse de l\'esclave (0-247, 0=broadcast).' },
      { field: 'Function Code', size: '1', desc: 'Code de la fonction Modbus.' },
      { field: 'Data', size: 'N', desc: 'Donnees de la requete/reponse.' },
    ],
  },
  rtu: {
    name: 'Modbus RTU (Serial)',
    fields: [
      { field: 'Address', size: '1', desc: 'Adresse esclave (1-247).' },
      { field: 'Function Code', size: '1', desc: 'Code de la fonction.' },
      { field: 'Data', size: 'N', desc: 'Donnees de la requete/reponse.' },
      { field: 'CRC', size: '2', desc: 'CRC-16 (little-endian).' },
    ],
  },
}

export const PROTOCOL_PATTERNS = [
  {
    name: 'Scan d\'appareils Modbus',
    desc: 'Identifier les esclaves actifs sur un bus.',
    code: [
      '# pymodbus scan',
      'from pymodbus.client import ModbusTcpClient',
      'client = ModbusTcpClient("192.168.1.100", port=502)',
      'client.connect()',
      'for uid in range(1, 248):',
      '    result = client.read_holding_registers(0, 1, slave=uid)',
      '    if not result.isError():',
      '        print(f"Esclave {uid} actif")',
    ],
  },
  {
    name: 'Lire des registres',
    desc: 'Lecture basique de holding registers.',
    code: [
      'result = client.read_holding_registers(',
      '    address=0,   # adresse de depart',
      '    count=10,    # nombre de registres',
      '    slave=1      # adresse esclave',
      ')',
      'print(result.registers)  # liste de valeurs 16-bit',
      '# Pour des floats (2 registres):',
      'import struct',
      'raw = struct.pack(">HH", regs[0], regs[1])',
      'value = struct.unpack(">f", raw)[0]',
    ],
  },
  {
    name: 'Ecrire des registres',
    desc: 'Ecriture de valeurs dans des holding registers.',
    code: [
      '# Single register',
      'client.write_register(address=0, value=100, slave=1)',
      '',
      '# Multiple registers',
      'client.write_registers(',
      '    address=0,',
      '    values=[100, 200, 300],',
      '    slave=1',
      ')',
      '',
      '# Coils (sortie discrete)',
      'client.write_coil(address=0, value=True, slave=1)',
    ],
  },
  {
    name: 'Identification d\'appareil',
    desc: 'Lire les infos d\'identification MEI.',
    code: [
      'from pymodbus.mei_message import ReadDeviceInformationRequest',
      'request = ReadDeviceInformationRequest(slave=1)',
      'result = client.execute(request)',
      '# result.information contient:',
      '# 0x00 = VendorName',
      '# 0x01 = ProductCode',
      '# 0x02 = MajorMinorRevision',
    ],
  },
]
