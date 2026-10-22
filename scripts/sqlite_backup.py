#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 SQLite 的在线备份接口复制数据库，保证拿到一致快照。

直接 Copy-Item 一个正在被写入的 .db（尤其是 WAL 模式）可能拷到半写状态，
sqlite3.Connection.backup() 会在读锁内做一致性拷贝，服务跑着也能用。

用法：
    python sqlite_backup.py <源.db> <目标.db>
"""
import sqlite3
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    source = sqlite3.connect(src, timeout=30)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    check = sqlite3.connect(dst)
    try:
        ok = check.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        check.close()
    print(f"  backup {src} -> {dst}  integrity={ok}")
    return 0 if ok == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
