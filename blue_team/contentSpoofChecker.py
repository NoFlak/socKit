#!/usr/bin/env python3
"""
contentSpoofChecker.py

Checks for content-type spoofing by comparing file extensions
against actual magic number signatures.
Outputs results to spoof_report.txt.
"""

import os

MAGIC_SIGNATURES = {
    "FFD8FF": "jpg",
    "89504E47": "png",
    "47494638": "gif",
    "25504446": "pdf",
    "504B0304": "zip/docx/xlsx",
    "377ABCAF": "7z",
    "4D5A": "exe/dll",
}

def read_magic_bytes(filepath, num_bytes=8):
    with open(filepath, 'rb') as f:
        return f.read(num_bytes).hex().upper()

def match_signature(magic_hex):
    for sig, filetype in MAGIC_SIGNATURES.items():
        if magic_hex.startswith(sig):
            return filetype
    return "unknown"

def check_file(filepath):
    _, ext = os.path.splitext(filepath)
    ext = ext.lower().strip('.')

    magic = read_magic_bytes(filepath)
    detected_type = match_signature(magic)

    return {
        "file": filepath,
        "extension": ext,
        "magic": magic,
        "detected_type": detected_type,
        "match": ext == detected_type
    }

def scan_directory(folder):
    results = []
    for root, _, files in os.walk(folder):
        for name in files:
            full_path = os.path.join(root, name)
            try:
                results.append(check_file(full_path))
            except Exception as e:
                results.append({"file": full_path, "error": str(e)})
    return results

def log_results(results, output_file="spoof_report.txt"):
    with open(output_file, 'w') as f:
        for r in results:
            if "error" in r:
                f.write(f"[ERROR] {r['file']}: {r['error']}\n")
            else:
                status = "✅ OK" if r["match"] else "❌ SPOOFED"
                f.write(f"{status} {r['file']} | Ext: {r['extension']} | Detected: {r['detected_type']} | Magic: {r['magic']}\n")

def main():
    scan_path = "uploads"  # Change to desired directory
    results = scan_directory(scan_path)
    log_results(results)
    print("🔍 Scan complete. Results saved to spoof_report.txt")

if __name__ == "__main__":
    main()
