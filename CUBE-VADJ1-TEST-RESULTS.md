# Fire TV Cube 3: October build hardware test results

**Result: successfully installed and passed the targeted repeated-playback test
on 15 November 2026.** The Cube owner confirmed normal TV blacks on the first
and fourth Plex plays.

## Tested package and setup

- Hardware: Amazon Fire TV Cube 3, T7/gazelle.
- Package: [`cube-vadj1-20261030-test1`](https://github.com/Radmeister/CoreELEC/releases/tag/cube-vadj1-20261030-test1), based on SamuriHL's `v22.0-samurihl-20261030200017` release.
- Running release after update: `22.0-Piers-samurihl_20261030200017`.
- Installation: verified update archive copied to `/storage/.update/`, normal
  update/reboot completed, installed kernel and SYSTEM hashes checked.
- Playback route: Plex add-on, including restarts through Plex's episode list;
  the test did not switch to a direct `Player.Open` stream.
- Media: same Plex-selected DV episode on all four starts; Kodi reported the
  title **Svoboda**, approximately 52:11 runtime. This is the media used for
  this test, rather than a claim that the earlier episode 5/6 pair was replayed.
- Processing/output: DV processor active; HDMI driver reported
  `HDR10-GAMMA_ST2084`, 4:2:2 12-bit.
- Original user-provided `dovi.ko` retained. No replacement DV module, capture
  configuration or persistent playback script was installed.
- The test setup's 2,150-nit preference and notification-only add-on update
  setting were preserved. Other displays should use their own appropriate settings.

## Repeated-play results

The driver readback used its existing register-read command for
`VPP_VADJ1_MISC` (`0x3280`). No manual register write or runtime bypass override was
used. Each play was paused near five seconds on the title card.

| Playback start | VADJ1 readback | Enable bit | DV processing | Reported output | Correction counter | TV confirmation |
|---|---|---|---|---|---:|---|
| First | `0x2` | Off | Active | HDR10 | 1 | Normal blacks |
| Second | `0x2` | Off | Active | HDR10 | 3 | Not separately requested |
| Third | `0x2` | Off | Active | HDR10 | 5 | Not separately requested |
| Fourth | `0x2` | Off | Active | HDR10 | 7 | Normal blacks |

The counter is `pq_vadj1_resyncs`: it counts correction requests, not playback
starts or independently confirmed hardware writes. The register readbacks and
TV confirmations provide the additional evidence of the resulting state.
The running correction switch reported `Y` throughout. No kernel BUG, Oops,
panic, call-trace or stack-corruption markers were detected; the final service
check reported no failed services. The update staging folder was empty afterward.

## Exact tested files

Update archive:

```
CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl_20261030200017-cube-vadj1-test1.tar
SHA256: 2e44c416e0af42f471d21cddbe79eea3ccdceb089908c5da320813b7eca034f9
```

Installed kernel:

```
c824dac6fce35598ffde86a7557c0ba4ca099eb752945f9f14cbb431e3569dfb
```

Installed SYSTEM:

```
974e37c3197d441acb928e4a5d99d37e40defd5d26694554978435cf160344eb
```

The update download, source bundle and original build reports have not been
rebuilt or replaced. Their recorded pre-test status is historical; this dated
report documents the later hardware validation.

## Scope

This confirms successful installation and the targeted repeated-play behaviour
on a Cube using the DV-to-HDR10 path. The first and fourth TV checks were visual;
the intermediate plays were verified by driver readback. No new numeric frame
capture or independent HDMI-wire measurement was made on this Cube. This was
not a broad SDR/HDR format, audio, CEC, suspend/resume or long-duration test.

The release remains an independent community prerelease, not a SamuriHL or
CoreELEC endorsement. Other devices and processing paths are not covered by
this result. The [earlier illustrated investigation](https://github.com/Radmeister/coreelec-cube-dv-fix/blob/main/TECHNICAL.md)
contains the original before/after captures and causal tests on the September
build; those captures are not presented as new October measurements.
