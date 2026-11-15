#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check all shipped ARM64 module imports against a rebuilt kernel/export set.

Run against the extracted, verified official SYSTEM (and extracted initramfs,
if it contains modules). Unchanged external module providers are also checked.
This checks symbol version compatibility, not runtime or picture correctness.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def symvers(path):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3:
            value = int(fields[0], 16)
            if fields[1] in result and result[fields[1]] != value:
                raise ValueError('Conflicting rebuilt export: ' + fields[1])
            result[fields[1]] = value
    return result


def elf_module(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('Expected uncompressed little-endian ARM64 ELF: ' + str(path))
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', data, 58)
    rows = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]

    def payload(section):
        return data[section[4]:section[4] + section[5]]

    def string(table, index):
        return table[index:].split(b'\0', 1)[0].decode('ascii')

    names = payload(rows[names_index])
    sections = {string(names, row[0]): row for row in rows}
    versions = payload(sections['__versions'])
    if len(versions) % 64:
        raise ValueError('Unexpected __versions size: ' + str(path))
    imports = {string(versions, i + 8): struct.unpack_from('<Q', versions, i)[0]
               for i in range(0, len(versions), 64)}
    exports = {}
    symbols = sections['.symtab']
    strings = payload(rows[symbols[6]])
    for index in range(symbols[5] // symbols[9]):
        name, _, _, section, value, _ = struct.unpack_from(
            '<IBBHQQ', data, symbols[4] + index * symbols[9])
        name = string(strings, name)
        if name.startswith('__crc_'):
            if section != 0xfff1:
                raise ValueError('Expected absolute module CRC: ' + name)
            exports[name[6:]] = value
    metadata = payload(sections['.modinfo']).split(b'\0')
    vermagic = [item[9:].decode('ascii') for item in metadata if item.startswith(b'vermagic=')]
    if len(vermagic) != 1 or vermagic[0] != '5.15.196 SMP preempt mod_unload modversions aarch64':
        raise ValueError('Unexpected module vermagic: ' + str(path) + ': ' + str(vermagic))
    return imports, exports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock-root', type=Path, action='append', required=True)
    parser.add_argument('--symvers', type=Path, required=True)
    parser.add_argument('--baseline-symvers', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rebuilt = symvers(args.symvers)
    export_changes = {}
    if args.baseline_symvers:
        baseline = symvers(args.baseline_symvers)
        export_changes = {name: [baseline.get(name), rebuilt.get(name)]
                          for name in baseline.keys() | rebuilt.keys()
                          if baseline.get(name) != rebuilt.get(name)}
    modules = []
    providers = {}
    for root in args.stock_root:
        for path in sorted(root.rglob('*.ko')):
            if path.is_symlink():
                continue
            imports, exports = elf_module(path)
            modules.append((str(path.relative_to(root)), imports))
            for name, crc in exports.items():
                providers.setdefault(name, set()).add(crc)
    if not modules:
        raise ValueError('No shipped modules found')
    checked = 0
    kernel_checks = 0
    retained_provider_checks = 0
    failures = []
    for path, imports in modules:
        for name, crc in imports.items():
            checked += 1
            if name in rebuilt:
                kernel_checks += 1
                if rebuilt[name] != crc:
                    failures.append({'module': path, 'symbol': name,
                                     'shipped_crc': hex(crc), 'rebuilt_crc': hex(rebuilt[name])})
            elif crc in providers.get(name, set()):
                retained_provider_checks += 1
            else:
                failures.append({'module': path, 'symbol': name, 'shipped_crc': hex(crc),
                                 'error': 'no matching rebuilt or retained stock provider'})
    report = {'passed': not failures and not export_changes,
              'modules_checked': len(modules), 'import_versions_checked': checked,
              'rebuilt_export_checks': kernel_checks,
              'unchanged_stock_module_provider_checks': retained_provider_checks,
              'rebuilt_exports': len(rebuilt), 'baseline_to_patched_export_changes': export_changes,
              'symvers_sha256': hashlib.sha256(args.symvers.read_bytes()).hexdigest(),
              'failures': failures,
              'limits': 'Symbol CRC/vermagic checks do not establish boot or playback correctness.'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
