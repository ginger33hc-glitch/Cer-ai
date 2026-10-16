"""Build a reproducible, source-only unpacked Chromium extension archive."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = ('manifest.json', 'background.js', 'bridge.js', 'adapter.js', 'receiver.js')


def build():
    output = ROOT / 'static' / 'cerai-escrs-assistant.zip'
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            entry = ZipInfo('cerai-escrs-assistant/' + name, (2026, 10, 16, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, (ROOT / 'extensions' / 'escrs-assistant' / name).read_bytes())
    return output


if __name__ == '__main__':
    print(build())
