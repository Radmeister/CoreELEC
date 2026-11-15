# Fire TV Cube 3: VADJ1 correction test branch

This community branch adds the measured raised-black correction to SamuriHL's
**v22.0-samurihl-20261030200017** release, commit
`bd95c331afe287a23f1851aab685fb2c6aa4907b`.

The October release retains the same affected `amve.c` as the September build.
The correction detects T7 VPP0 hardware still enabling VADJ1 while STB Dolby
Vision bypass requests it off, and reuses the existing direct/RDMA disable path.
It preserves the other register bits, Dolby-generated settings, and the intended
DV-to-HDR10 processing path.

## Source change

The correction is carried by:

```
projects/Amlogic-ce/packages/linux-drivers/amlogic/common_drivers/patches/0023-amvecm-t7-reconcile-vadj1-dv-bypass.patch
```

Matching assertions check the helper and both write-path call sites. No other
picture-processing source change is introduced. The resulting `amve.c` is
byte-identical to the correction previously validated on two Cubes using the
September release. The October kernel still requires its own compatibility and
hardware validation; prior tests do not establish that this new build works.

[Detailed findings, original captures, raw readings and maintainer checklist](https://github.com/Radmeister/coreelec-cube-dv-fix/blob/main/TECHNICAL.md).

## Building

Use the usual CoreELEC build environment for this source branch:

```sh
PROJECT=Amlogic-ce DEVICE=Amlogic-no ARCH=aarch64 make image
```

The common_drivers recipe applies patch 0023 during the build. This modifies the
host media driver in the kernel; a replacement `dovi.ko` is unnecessary.

The community update package is assembled from the verified official October
update with a rebuilt matching kernel. Its official system image, initramfs,
device trees, bootloader files and licenses are preserved. The kernel checksum
is updated. The release's stock embedded kernel configuration is used for the
rebuild, and shipped-module ABI checks are required before publishing the test
archive. Build/packaging verification results accompany the release.

## Testing the update

Use the community `.tar` attached to this fork's test release only after its
build verification is complete. It is intended for **Fire TV Cube 3** testing;
do not apply the older September kernel installer after updating.

1. Keep a full backup and a known-working recovery/update archive.
2. Copy the verified community update `.tar` into `/storage/.update/`.
3. Reboot into CoreELEC using the Cube's configured boot method.
4. Check the running guard:

   ```sh
   cat /sys/module/aml_media/parameters/pq_vadj1_sync
   ```

   It should report `Y`.
5. Play the same affected DV file repeatedly through Plex, then another file,
   checking the same dark scene. Confirm the intended HDR10 output is retained.

Keep Kodi add-on updates on notification-only mode if using the workaround for
the separately observed startup/update deadlock. That issue is independent of
this kernel correction.

This is an independent community test build, not a SamuriHL/CoreELEC release or
endorsement. Do not overwrite a working reference device before verifying a test
Cube. The VADJ1 change activates only on T7 VPP0 in the specified DV bypass state.
