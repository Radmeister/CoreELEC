#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Reconstruct the exact uncorrected October kernel from the source bundle."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--inputs', type=Path, required=True)
parser.add_argument('--build-root', type=Path, required=True)
args = parser.parse_args()
inputs = args.inputs.resolve()
build = args.build_root.resolve()
hashes = {
    'recipe-source.tar.gz': '5c5010bf1104b541f15b3754ad9585d321411055197be58747ccf4a2f0cb0022',
    'kernel-source.tar.gz': '75075216239ead69b8f302355ec9724f7852aaf96ff17399effb67ab0b1dc0cc',
    'common-drivers.tar.gz': '1859998ce9e1bd2369a76211fe85a51f284dc7b164d3296054b5d68fe6acbeb2',
    'bl30.tar.gz': 'cc79de0b7e0829648ce950579236b26ee4e129a01d9e75cd55efc828126fa3a6',
    'stock.config': 'ebd75ec492d9d9aa1693379859a3036143b9f079b1dbb421183550e0b2f126e3',
    '0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch': 'c78a97133c2dd4c966197a1060c09f99884d9714f30d159ca57f57b15335d18c',
}
for name, expected in hashes.items():
    if hashlib.sha256((inputs / name).read_bytes()).hexdigest() != expected:
        raise ValueError('Source bundle input checksum failed: ' + name)
kernel = build / 'kernel'
recipe = build / 'recipe'
bl30 = build / 'bl30'
if any(path.exists() for path in [kernel, recipe, bl30]):
    raise ValueError('Use a fresh build directory; existing work is never removed')
for path, archive in [(kernel, 'kernel-source.tar.gz'), (recipe, 'recipe-source.tar.gz'),
                      (bl30, 'bl30.tar.gz')]:
    path.mkdir(parents=True)
    subprocess.run(['tar', '-xzf', str(inputs / archive), '--strip-components=1', '-C', str(path)], check=True)
drivers = kernel / 'common_drivers'
drivers.mkdir(exist_ok=True)
subprocess.run(['tar', '-xzf', str(inputs / 'common-drivers.tar.gz'), '--strip-components=1',
                '-C', str(drivers)], check=True)
patches = recipe / 'projects/Amlogic-ce/packages/linux-drivers/amlogic/common_drivers/patches'
patch_files = sorted(patches.glob('*.patch'))
if len(patch_files) != 18:
    raise ValueError('Expected the unmodified release recipe with 18 driver patches')
for patch in patch_files:
    subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)], cwd=drivers, check=True)
subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(recipe /
                'projects/Amlogic-ce/devices/Amlogic-no/patches/linux/linux-04-xpadneo.patch')],
               cwd=kernel, check=True)
shutil.copyfile(inputs / 'stock.config', kernel / '.config')
(kernel / '.scmversion').write_text('')
(drivers / '.scmversion').write_text('f9af0b41d6da6cd501b75c33bf44338693195d96\n')
makefile = kernel / 'Makefile'
text = makefile.read_text()
text = re.sub(r'^KBUILD_CFLAGS \+= \$\(call cc-option,-Wimplicit-fallthrough,\).*$', '', text, flags=re.M)
text = re.sub(r'^KBUILD_CFLAGS   := (.*)$',
              r'KBUILD_CFLAGS   := -Wno-format -Wno-unused-function -Wno-misleading-indentation \1', text, flags=re.M)
text = re.sub(r'^KBUILD_LDFLAGS :=', r'KBUILD_LDFLAGS := $(call ld-option,--no-warn-rwx-segments)', text, flags=re.M)
makefile.write_text(text)
arm = kernel / 'arch/arm64/Makefile'
arm.write_text(arm.read_text().replace('-z norelro', ''))
release_recipe = (recipe / 'projects/Amlogic-ce/packages/linux/package.mk').read_text()
expected = release_recipe[release_recipe.index('build_gpio_data() {'):release_recipe.index('\npre_make_target()')].strip()
generator = (inputs / 'generate-gpio.sh').read_text()
actual = generator[generator.index('build_gpio_data() {'):generator.rindex('\nbuild_gpio_data')].strip()
if expected != actual:
    raise ValueError('GPIO generator differs from release recipe')
subprocess.run(['bash', str(inputs / 'generate-gpio.sh'), str(bl30), str(kernel)], check=True)
amve = drivers / 'drivers/media/enhancement/amvecm/amve.c'
if hashlib.sha256(amve.read_bytes()).hexdigest() != '2ca8054e10e1339ab435c4b1d0069d423c50b5a02326821af6f1a454cfd7d24b':
    raise ValueError('Reconstructed baseline driver differs from release')
print(json.dumps({'prepared': True, 'kernel': str(kernel), 'release_driver_patches': len(patch_files)}))
