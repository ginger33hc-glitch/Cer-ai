from pathlib import Path
import subprocess


def test_slow_network_input_queue():
    result = subprocess.run(['node', 'tests/escrs-input-queue.test.cjs'],
                            cwd=Path(__file__).parents[1], capture_output=True,
                            text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
