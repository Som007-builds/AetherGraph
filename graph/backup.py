# graph/backup.py
"""
Neo4j backup utility.
Creates a timestamped dump of the Neo4j database via neo4j-admin inside Docker.

Usage:
    python main.py --mode backup
    # or directly:
    python graph/backup.py
"""
import subprocess
from datetime import datetime
from pathlib import Path
from config import NEO4J_CONTAINER_NAME

BACKUP_DIR = Path("data/backups")


def create_backup() -> Path:
    """
    Dumps the Neo4j database to data/backups/neo4j-YYYY-MM-DD-HHMM.dump
    Returns the path to the dump file.
    Raises RuntimeError if neo4j-admin fails.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    dump_filename = f"neo4j-{timestamp}.dump"
    container_dump_path = f"/tmp/{dump_filename}"
    local_dump_path = BACKUP_DIR / dump_filename

    print(f"Creating Neo4j backup: {dump_filename}")

    # Dump inside the container
    result = subprocess.run([
        "docker", "exec", NEO4J_CONTAINER_NAME,
        "neo4j-admin", "database", "dump",
        "--to-path=/tmp/",
        "neo4j"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"neo4j-admin dump failed:\n{result.stderr}"
        )

    # Copy dump out of the container
    subprocess.run([
        "docker", "cp",
        f"{NEO4J_CONTAINER_NAME}:{container_dump_path}",
        str(local_dump_path)
    ], check=True)

    size_mb = local_dump_path.stat().st_size / (1024 * 1024)
    print(f"Backup saved: {local_dump_path} ({size_mb:.1f} MB)")
    return local_dump_path


def list_backups() -> list[Path]:
    """Returns all backup dump files, newest first."""
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("neo4j-*.dump"), reverse=True)


def prune_old_backups(keep: int = 7):
    """Delete all but the N most recent backups."""
    backups = list_backups()
    to_delete = backups[keep:]
    for b in to_delete:
        b.unlink()
        print(f"Pruned old backup: {b.name}")


if __name__ == "__main__":
    create_backup()
    prune_old_backups(keep=7)
    print("\nAll backups:")
    for b in list_backups():
        print(f"  {b.name}")