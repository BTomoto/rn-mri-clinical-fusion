"""Read public ZIP/ZIP64 members using verified HTTP byte ranges.

No authentication is required for the Figshare archives used by this project.
Member contents are checked against the ZIP's uncompressed size and CRC32.
"""
from __future__ import annotations
import concurrent.futures
import json
import struct
import time
import urllib.request
import zlib
from pathlib import Path


def range_bytes(url: str, start: int, length: int, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start+length-1}"})
            with urllib.request.urlopen(req, timeout=55) as response:
                cr = response.headers.get("Content-Range", "")
                if response.status != 206 or not cr.startswith(f"bytes {start}-"):
                    raise ValueError("Server did not honor the requested byte range")
                data = response.read(length + 1)
            if len(data) != length:
                raise ValueError(f"Incomplete range: {len(data)} != {length}")
            return data
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable")


def parse_directory(data: bytes) -> list[dict]:
    entries = []
    p = 0
    while p + 46 <= len(data) and data[p:p+4] == b"PK\x01\x02":
        h = struct.unpack_from("<4s6H3L5H2L", data, p)
        nl, el, cl = h[10:13]
        name_bytes = data[p+46:p+46+nl]
        name = name_bytes.decode("utf-8" if h[3] & 0x800 else "cp437")
        extra = data[p+46+nl:p+46+nl+el]
        us, cs, off = h[9], h[8], h[16]
        ep = 0
        while ep + 4 <= len(extra):
            kind, size = struct.unpack_from("<HH", extra, ep)
            payload = extra[ep+4:ep+4+size]
            if kind == 1:
                zp = 0
                if us == 0xFFFFFFFF:
                    us = struct.unpack_from("<Q", payload, zp)[0]; zp += 8
                if cs == 0xFFFFFFFF:
                    cs = struct.unpack_from("<Q", payload, zp)[0]; zp += 8
                if off == 0xFFFFFFFF:
                    off = struct.unpack_from("<Q", payload, zp)[0]
            ep += 4 + size
        entries.append(dict(name=name, compressed_size=cs, size=us, crc32=h[7],
                            compression=h[4], offset=off, name_bytes=nl))
        p += 46 + nl + el + cl
    if p != len(data):
        raise ValueError(f"Unparsed central-directory bytes: {len(data)-p}")
    return entries


def fetch_directory(url: str, archive_size: int) -> bytes:
    size = min(131072, archive_size)
    tail = range_bytes(url, archive_size-size, size)
    e = tail.rfind(b"PK\x05\x06")
    if e < 0:
        raise ValueError("ZIP end-of-directory record missing")
    h = struct.unpack_from("<4s4H2LH", tail, e)
    cs, off = h[5:7]
    if off == 0xFFFFFFFF or cs == 0xFFFFFFFF:
        z = tail.rfind(b"PK\x06\x06")
        if z < 0:
            raise ValueError("ZIP64 directory record missing from tail")
        zh = struct.unpack_from("<4sQ2H2L4Q", tail, z)
        cs, off = zh[-2:]
    return range_bytes(url, off, cs)


def extract_member(block: bytes, block_start: int, entry: dict) -> bytes:
    p = entry["offset"] - block_start
    if block[p:p+4] != b"PK\x03\x04":
        raise ValueError(f"Local header missing: {entry['name']}")
    nl, el = struct.unpack_from("<HH", block, p+26)
    p += 30 + nl + el
    compressed = block[p:p+entry["compressed_size"]]
    if entry["compression"] == 0:
        result = compressed
    elif entry["compression"] == 8:
        result = zlib.decompress(compressed, -15)
    else:
        raise ValueError(f"Unsupported ZIP compression {entry['compression']}")
    if len(result) != entry["size"] or zlib.crc32(result) & 0xFFFFFFFF != entry["crc32"]:
        raise ValueError(f"Size/CRC mismatch: {entry['name']}")
    return result


def download_members(url: str, entries: list[dict], destination: Path, workers: int = 6) -> dict:
    """Resume verified members; batch nearby members into <=16 MiB requests."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    pending = []
    skipped = 0
    for e in sorted(entries, key=lambda x: x["offset"]):
        target = (destination / e["name"]).resolve()
        if destination not in target.parents:
            raise ValueError("Unsafe ZIP member path")
        if target.is_file() and target.stat().st_size == e["size"]:
            with target.open("rb") as stream:
                crc = 0
                for chunk in iter(lambda: stream.read(1024*1024), b""):
                    crc = zlib.crc32(chunk, crc)
            if crc & 0xFFFFFFFF == e["crc32"]:
                skipped += 1
                continue
        pending.append(e)
    batches = []
    current = []
    start = end = 0
    for e in pending:
        # Includes enough room for the local extra field; archive offsets locate every member.
        ee = e["offset"] + 30 + e["name_bytes"] + 256 + e["compressed_size"]
        if current and (e["offset"]-end > 65536 or ee-start > 16*1024*1024):
            batches.append((start, end, current)); current = []
        if not current:
            start = e["offset"]
        end = max(ee, end) if current else ee
        current.append(e)
    if current:
        batches.append((start, end, current))

    def work(batch):
        a, b, members = batch
        block = range_bytes(url, a, b-a)
        for entry in members:
            raw = extract_member(block, a, entry)
            target = destination / entry["name"]
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".partial")
            temporary.write_bytes(raw)
            temporary.replace(target)
        return len(members), b-a

    downloaded = transferred = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for n, count in pool.map(work, batches):
            downloaded += n; transferred += count
    return dict(downloaded_members=downloaded, verified_existing=skipped,
                transferred_bytes=transferred, batches=len(batches))
