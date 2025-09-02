#!/usr/bin/env python3
"""Update project memory and index into knowledge database."""

import argparse
import json
import pathlib
import datetime
import sqlite3
import uuid
import sys

def iso_now():
    """Get current UTC time in ISO format."""
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filepath, data):
    """Save JSON file with proper formatting."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_project(db, project_id, project_name=None, client=None, location=None):
    """Ensure project exists in database."""
    cur = db.cursor()
    cur.execute("SELECT id FROM projects WHERE id=?", (project_id,))
    row = cur.fetchone()
    now = iso_now()
    
    if row is None:
        cur.execute(
            "INSERT INTO projects(id, name, client, location, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (project_id, project_name or project_id, client, location, now, now)
        )
    else:
        cur.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
    
    db.commit()

def index_records(db, project_id, file_path, collection, items):
    """Index records into the database."""
    cur = db.cursor()
    now = iso_now()
    
    for rec in items:
        rec_id = rec.get("id") or str(uuid.uuid4())
        
        # Build summary from various possible fields
        summary_fields = ["summary", "title", "purpose", "question", "rationale", "decision", "name", "description"]
        summary = ""
        for field in summary_fields:
            if field in rec and rec[field]:
                summary = str(rec[field])
                break
        
        # Build tags
        tag_list = rec.get("tags", [])
        if "type" in rec:
            tag_list.append(rec["type"])
        tag_list.append(collection)
        tags = ",".join(set(str(t) for t in tag_list))
        
        # Get status
        status = rec.get("status", "active")
        
        # Store record
        cur.execute(
            """INSERT OR REPLACE INTO records(
                id, project_id, collection, record_json, summary, tags, 
                status, last_updated, file_path
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            (rec_id, project_id, collection, json.dumps(rec, ensure_ascii=False), 
             summary, tags, status, now, str(file_path))
        )
    
    db.commit()

def apply_updates(memory, updates):
    """Apply updates to memory structure."""
    update_count = 0
    
    for upd in updates.get("updates", []):
        coll = upd["collection"]
        rec = upd["record"]
        
        # Ensure collection exists
        if coll not in memory:
            memory[coll] = []
        
        # Add record ID if missing
        if "id" not in rec:
            rec["id"] = f"{coll[:2]}-{str(uuid.uuid4())[:8]}"
        
        # Add timestamp if missing
        if "created_at" not in rec:
            rec["created_at"] = iso_now()
        
        memory[coll].append(rec)
        update_count += 1
    
    return update_count

def main():
    """Main entry point."""
    ap = argparse.ArgumentParser(description="Update project memory and knowledge database")
    ap.add_argument("--project", default=".", help="Project folder path (default: current directory)")
    ap.add_argument("--update", help="JSON file containing updates")
    ap.add_argument("--init", action="store_true", help="Initialize memory files if they don't exist")
    
    args = ap.parse_args()
    
    # Resolve paths
    if args.project == ".":
        project_dir = pathlib.Path.cwd()
    else:
        project_dir = pathlib.Path(args.project).resolve()
    
    memory_path = project_dir / "project_memory.json"
    log_path = project_dir / "project_log.md"
    db_path = project_dir / "knowledge.db"
    
    # Initialize if requested
    if args.init:
        if not memory_path.exists():
            print(f"Initializing project memory at {memory_path}")
            initial_memory = {
                "project": {
                    "id": project_dir.name.upper(),
                    "name": project_dir.name,
                    "client": "",
                    "location": str(project_dir),
                    "created_at": iso_now(),
                    "updated_at": iso_now(),
                    "owners": []
                },
                "equipment_assets": [],
                "configs_network": [],
                "known_problems": [],
                "procedures_code": [],
                "milestones_decisions": [],
                "open_questions": [],
                "documents": [],
                "audit_trail": []
            }
            save_json(memory_path, initial_memory)
        
        if not log_path.exists():
            with open(log_path, "w") as f:
                f.write(f"# {project_dir.name} Project Log\n\n")
                f.write(f"**Started:** {datetime.date.today().isoformat()}\n\n")
        
        print("✓ Initialization complete")
        return
    
    # Load memory
    if not memory_path.exists():
        print(f"Error: Project memory not found at {memory_path}")
        print("Run with --init to initialize project files")
        sys.exit(1)
    
    memory = load_json(memory_path)
    
    # Apply updates if provided
    if args.update:
        update_path = pathlib.Path(args.update)
        if not update_path.exists():
            print(f"Error: Update file not found at {update_path}")
            sys.exit(1)
        
        updates = load_json(update_path)
        
        if updates.get("intent") != "append_records":
            print("Error: Only 'append_records' intent is supported")
            sys.exit(1)
        
        # Apply updates
        count = apply_updates(memory, updates)
        
        # Update timestamps and audit trail
        memory["project"]["updated_at"] = iso_now()
        memory.setdefault("audit_trail", []).append({
            "action": "append_records",
            "by": updates.get("by", "assistant"),
            "timestamp": iso_now(),
            "notes": f"Added {count} record(s) via update_memory.py"
        })
        
        # Save updated memory
        save_json(memory_path, memory)
        
        # Update log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {datetime.date.today().isoformat()}\n")
            f.write(f"- Added {count} records via memory update\n")
        
        # Index into database if it exists
        if db_path.exists():
            con = sqlite3.connect(str(db_path))
            
            # Ensure project exists
            proj = memory["project"]
            ensure_project(con, proj["id"], proj.get("name"), 
                         proj.get("client"), proj.get("location"))
            
            # Index all updates
            for upd in updates.get("updates", []):
                index_records(con, proj["id"], memory_path, 
                            upd["collection"], [upd["record"]])
            
            con.close()
            print(f"✓ Indexed {count} records into knowledge.db")
        
        print(f"✓ Updated {count} records in project memory")
    
    else:
        # Just display current status
        proj = memory["project"]
        print(f"Project: {proj['name']} ({proj['id']})")
        print(f"Location: {memory_path}")
        print(f"Last Updated: {proj.get('updated_at', 'Unknown')}")
        print("\nCollections:")
        for key, value in memory.items():
            if key not in ["project", "audit_trail"] and isinstance(value, list):
                print(f"  {key}: {len(value)} records")

if __name__ == "__main__":
    main()
