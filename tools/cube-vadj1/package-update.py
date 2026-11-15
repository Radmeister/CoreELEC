#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Repack the pinned October release, changing only KERNEL and its MD5.

Usage: package-update.py STOCK.tar Image.corrected.lzo ABI-CHECK.json OUTPUT.tar
The kernel must already have been compiled and checked against stock modules.
This script never accesses a player or installs an update.
"""
import copy
import hashlib
import io
import json
import struct
import sys
import tarfile
from pathlib import Path

STOCK_SHA = '9949947f35fb64ca3ab0ef81a6d96a6fba069908765382fd971f88acccb25a4c'
KERNEL_SHA = 'ee436f421114722413b46a75260e5e19d36e9c697dba8a11257560406af73d85'
ROOT = 'CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl_20261030200017'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with path.open('rb') as handle:
        return stream_digest(handle)


def stream_digest(handle, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def unpack(data):
    if data[:8] != b'ANDROID!':
        raise ValueError('Wrong Android boot magic')
    kernel, _, ramdisk, _, second, _, _, page, version, _ = struct.unpack_from('<10I', data, 8)
    if page != 2048 or version != 0 or second:
        raise ValueError('Unexpected Android boot layout')
    align = lambda n: (n + page - 1) // page * page
    rp = page + align(kernel)
    end = rp + align(ramdisk)
    if end != len(data):
        raise ValueError('Unexpected boot image trailer')
    parts = [data[page:page + kernel], data[rp:rp + ramdisk], b'']
    h = hashlib.sha1()
    for part in parts:
        h.update(part)
        h.update(struct.pack('<I', len(part)))
    if data[576:596] != h.digest():
        raise ValueError('Android boot ID mismatch')
    return {'header': data[:page], 'kernel': parts[0], 'ramdisk': parts[1],
            'kernel_padding': data[page + kernel:rp], 'ramdisk_padding': data[rp + ramdisk:end]}


def boot_image(original, kernel):
    parts = unpack(original)
    roundtrip = (parts['header'] + parts['kernel'] + parts['kernel_padding'] +
                 parts['ramdisk'] + parts['ramdisk_padding'])
    if roundtrip != original:
        raise ValueError('Original boot image roundtrip failed')
    if not kernel.startswith(b'\x89LZO\x00\r\n\x1a\n'):
        raise ValueError('Expected lzop kernel payload')
    header = bytearray(parts['header'])
    struct.pack_into('<I', header, 8, len(kernel))
    h = hashlib.sha1()
    for part in (kernel, parts['ramdisk'], b''):
        h.update(part)
        h.update(struct.pack('<I', len(part)))
    header[576:596] = h.digest()
    result = bytes(header) + kernel + bytes((-len(kernel)) % 2048) + parts['ramdisk'] + parts['ramdisk_padding']
    verify = unpack(result)
    expected = bytearray(parts['header'])
    expected[8:12] = verify['header'][8:12]
    expected[576:596] = verify['header'][576:596]
    if bytes(expected) != verify['header'] or verify['ramdisk'] != parts['ramdisk']:
        raise ValueError('Unexpected boot header or initramfs change')
    return result, {'original_roundtrip_exact': True, 'initramfs_unchanged': True,
                    'initramfs_sha256': digest(parts['ramdisk']),
                    'header_only_changes': ['kernel_size', 'standard_boot_id']}


def attributes(member):
    return {name: getattr(member, name) for name in
            ['name', 'mode', 'uid', 'gid', 'mtime', 'type', 'linkname', 'uname', 'gname',
             'devmajor', 'devminor', 'pax_headers']}


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    stock, image, abi_path, output = map(Path, sys.argv[1:])
    if output.exists():
        raise ValueError('Output already exists')
    if file_digest(stock) != STOCK_SHA:
        raise ValueError('Wrong official update archive')
    abi = json.loads(abi_path.read_text())
    if not abi.get('passed') or abi.get('baseline_to_patched_export_changes'):
        raise ValueError('Module ABI checks have not passed')
    kernel_path = ROOT + '/target/KERNEL'
    md5_path = kernel_path + '.md5'
    with tarfile.open(stock) as source:
        old_kernel = source.extractfile(kernel_path).read()
        if digest(old_kernel) != KERNEL_SHA:
            raise ValueError('Wrong official boot image')
        corrected, boot_report = boot_image(old_kernel, image.read_bytes())
        old_md5 = source.extractfile(md5_path).read()
        expected_md5 = (hashlib.md5(old_kernel).hexdigest() + '  target/KERNEL\n').encode()
        if old_md5 != expected_md5:
            raise ValueError('Unexpected official KERNEL.md5')
        replacements = {kernel_path: corrected,
                        md5_path: (hashlib.md5(corrected).hexdigest() + '  target/KERNEL\n').encode()}
        with tarfile.open(output, 'x', format=tarfile.GNU_FORMAT) as target:
            for member in source:
                updated = copy.copy(member)
                if member.name in replacements:
                    data = replacements[member.name]
                    updated.size = len(data)
                    target.addfile(updated, io.BytesIO(data))
                else:
                    target.addfile(updated, source.extractfile(member) if member.isfile() else None)
    changed = []
    unchanged = 0
    with tarfile.open(stock) as source, tarfile.open(output) as target:
        before, after = source.getmembers(), target.getmembers()
        if len(before) != len(after) or len(before) != 236:
            raise ValueError('Archive entry count changed')
        for a, b in zip(before, after):
            if attributes(a) != attributes(b):
                raise ValueError('Archive metadata changed: ' + a.name)
            if a.isfile():
                old = stream_digest(source.extractfile(a))
                new = stream_digest(target.extractfile(b))
                if old != new:
                    changed.append(a.name)
                    if a.name not in replacements or new != digest(replacements[a.name]):
                        raise ValueError('Incorrect replacement: ' + a.name)
                else:
                    unchanged += 1
        if set(changed) != set(replacements):
            raise ValueError('Unexpected archive content changes: ' + repr(changed))
        system_sha = stream_digest(target.extractfile(ROOT + '/target/SYSTEM'))
        computed_system_md5 = stream_digest(target.extractfile(ROOT + '/target/SYSTEM'), 'md5')
        system_md5 = target.extractfile(ROOT + '/target/SYSTEM.md5').read()
        if system_md5 != (computed_system_md5 + '  target/SYSTEM\n').encode():
            raise ValueError('SYSTEM checksum verification failed')
    report = {'passed': True, 'stock_update_sha256': STOCK_SHA,
              'community_update_sha256': file_digest(output), 'community_update_bytes': output.stat().st_size,
              'stock_kernel_sha256': KERNEL_SHA, 'corrected_kernel_sha256': digest(corrected),
              'corrected_lzo_sha256': file_digest(image), 'system_sha256': system_sha,
              'archive_entries_checked': len(before), 'unchanged_regular_files': unchanged,
              'only_changed_entries': changed, 'all_member_metadata_preserved': True,
              'boot': boot_report, 'module_abi': abi, 'hardware_test_pending': True}
    report_path = output.with_suffix('.verification.json')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    output.with_suffix('.tar.sha256').write_text(report['community_update_sha256'] + '  ' + output.name + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
