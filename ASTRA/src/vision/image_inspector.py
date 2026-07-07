import struct
from pathlib import Path


class ImageInspectionError(Exception):
    pass


class ImageInspector:
    """Dependency-free metadata inspection for explicit local image paths."""

    def inspect(self, image_path):
        path = Path(str(image_path).strip().strip('"'))
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        if not path.is_file():
            raise ImageInspectionError(f"Not a file: {image_path}")
        with open(path, "rb") as handle:
            header = handle.read(64)
            handle.seek(0)
            size = path.stat().st_size
            kind, width, height = inspect_header(header, handle)
        return {
            "path": str(path),
            "format": kind,
            "width": width,
            "height": height,
            "bytes": size,
        }


def inspect_header(header, handle):
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        width, height = struct.unpack(">II", header[16:24])
        return "PNG", width, height
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        width, height = struct.unpack("<HH", header[6:10])
        return "GIF", width, height
    if header.startswith(b"\xff\xd8"):
        width, height = inspect_jpeg(handle)
        return "JPEG", width, height
    raise ImageInspectionError("Unsupported image format. Supported: PNG, JPEG, GIF.")


def inspect_jpeg(handle):
    handle.seek(2)
    while True:
        marker_start = handle.read(1)
        if marker_start != b"\xff":
            raise ImageInspectionError("Invalid JPEG marker stream.")
        marker = handle.read(1)
        while marker == b"\xff":
            marker = handle.read(1)
        if marker in {b"\xd8", b"\xd9"}:
            continue
        length_bytes = handle.read(2)
        if len(length_bytes) != 2:
            raise ImageInspectionError("Truncated JPEG segment.")
        segment_length = struct.unpack(">H", length_bytes)[0]
        if segment_length < 2:
            raise ImageInspectionError("Invalid JPEG segment length.")
        if marker in {
            b"\xc0",
            b"\xc1",
            b"\xc2",
            b"\xc3",
            b"\xc5",
            b"\xc6",
            b"\xc7",
            b"\xc9",
            b"\xca",
            b"\xcb",
            b"\xcd",
            b"\xce",
            b"\xcf",
        }:
            payload = handle.read(5)
            if len(payload) != 5:
                raise ImageInspectionError("Truncated JPEG size segment.")
            height, width = struct.unpack(">HH", payload[1:5])
            return width, height
        handle.seek(segment_length - 2, 1)
