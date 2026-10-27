"""
Unit tests for the Nexthop U-Boot env vendor hook.

The shared Aspeed TFTP installer stages this hook for every AST2700 board, so
it must set boot_guard to nh_stormguard only on Nexthop boards: any other
U-Boot lacks that command and would stop at its prompt instead of booting.
"""

import os
import subprocess

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
NEXTHOP_DIR = os.path.dirname(TEST_DIR)
HOOK_PATH = os.path.join(
    NEXTHOP_DIR, "common", "scripts", "sonic-uboot-env-vendor-hook")

NEXTHOP_COMPATIBLE = b"nexthop,nexthop-b27-r0\0aspeed,ast2700\0"
OTHER_COMPATIBLE = b"aspeed,ast2700-evb\0aspeed,ast2700\0"


def run_hook(tmp_path, compatible):
    """Run the hook with a stub fw_setenv; return (exit code, fw_setenv calls, stderr)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "fw_setenv.calls"
    fw_setenv = bin_dir / "fw_setenv"
    fw_setenv.write_text('#!/bin/sh\necho "$*" >> "%s"\n' % calls)
    fw_setenv.chmod(0o755)

    dt_compatible = tmp_path / "compatible"
    if compatible is not None:
        dt_compatible.write_bytes(compatible)

    env = dict(os.environ,
               PATH="%s:%s" % (bin_dir, os.environ.get("PATH", "")),
               DT_COMPATIBLE=str(dt_compatible))
    env.pop("SONIC_UBOOT_ENV_LOG_FILE", None)
    result = subprocess.run(["sh", HOOK_PATH], env=env,
                            capture_output=True, check=False)
    lines = calls.read_text().splitlines() if calls.exists() else []
    return result.returncode, lines, result.stderr.decode()


def test_nexthop_board_sets_stormguard(tmp_path):
    rc, calls, _ = run_hook(tmp_path, NEXTHOP_COMPATIBLE)
    assert rc == 0
    assert calls == ["boot_guard nh_stormguard"]


def test_other_board_keeps_default_boot_guard(tmp_path):
    rc, calls, _ = run_hook(tmp_path, OTHER_COMPATIBLE)
    assert rc == 0
    assert calls == []


def test_unreadable_device_tree_keeps_default_boot_guard(tmp_path):
    rc, calls, stderr = run_hook(tmp_path, None)
    assert rc == 0
    assert calls == []
    assert stderr == "Not a Nexthop board, keeping default boot_guard\n"
