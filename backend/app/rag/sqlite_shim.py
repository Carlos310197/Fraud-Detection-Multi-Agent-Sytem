"""
SQLite3 compatibility shim for ChromaDB on AWS Lambda.

AWS Lambda's Python 3.11 runtime includes SQLite 3.7.17, but ChromaDB requires
SQLite 3.35.0 or higher. This module swaps the system sqlite3 module with 
pysqlite3, which bundles a newer SQLite version.

Import this module BEFORE importing chromadb to ensure compatibility.
"""
import sys

# Check if we need the shim (Lambda environment)
try:
    import sqlite3
    version = sqlite3.sqlite_version_info
    
    # Only swap if SQLite is older than 3.35
    if version < (3, 35, 0):
        # Use pysqlite3 instead of the system sqlite3 if available
        try:
            import pysqlite3  # type: ignore
            sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
            print(
                f"SQLite shim activated: replaced {sqlite3.sqlite_version} with {pysqlite3.sqlite_version}"
            )
        except ImportError:
            # pysqlite3 not available: continue with system sqlite3.
            # On AWS Lambda with old SQLite, ChromaDB may fail to import.
            pass
except Exception:
    # Defensive: never crash application import due to the shim.
    pass
