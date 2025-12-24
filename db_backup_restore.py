"""
Database Backup and Restore Script
Provides functionality to backup all tables to JSON files and restore them with table selection.
"""

import os
import json
import asyncio
import logging
import asyncpg
from dotenv import load_dotenv
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")
DEFAULT_BACKUP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database_backup")


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle PostgreSQL-specific types like UUID, datetime, Decimal, etc.
    """
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        return super().default(obj)


def json_serializer(record: dict) -> dict:
    """
    Converts a database record to a JSON-serializable dictionary.
    """
    result = {}
    for key, value in record.items():
        if isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, bytes):
            result[key] = value.decode('utf-8', errors='replace')
        else:
            result[key] = value
    return result


async def get_all_tables(conn: asyncpg.Connection) -> list[str]:
    """
    Fetches all table names from the public schema.
    """
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name;
    """
    rows = await conn.fetch(query)
    return [row['table_name'] for row in rows]


async def get_table_data(conn: asyncpg.Connection, table_name: str) -> list[dict]:
    """
    Fetches all data from a specific table.
    """
    query = f'SELECT * FROM "{table_name}"'
    rows = await conn.fetch(query)
    return [json_serializer(dict(row)) for row in rows]


async def get_table_schema(conn: asyncpg.Connection, table_name: str) -> list[dict]:
    """
    Fetches the schema information for a specific table.
    """
    query = """
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length
    FROM information_schema.columns
    WHERE table_schema = 'public' 
    AND table_name = $1
    ORDER BY ordinal_position;
    """
    rows = await conn.fetch(query, table_name)
    return [dict(row) for row in rows]


async def backup_database(backup_folder: Optional[str] = None):
    """
    Backs up all tables in the database to JSON files in the specified folder.
    """
    folder = backup_folder or DEFAULT_BACKUP_FOLDER
    
    if not os.path.exists(folder):
        os.makedirs(folder)
        logger.info(f"Created backup folder: {folder}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subfolder = os.path.join(folder, f"backup_{timestamp}")
    os.makedirs(backup_subfolder)
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Connected to database successfully")
        
        tables = await get_all_tables(conn)
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        metadata = {
            "backup_timestamp": datetime.now().isoformat(),
            "tables": [],
            "database_url_masked": DATABASE_URL[:20] + "..." if DATABASE_URL else None
        }
        
        for table_name in tables:
            logger.info(f"Backing up table: {table_name}")
            
            data = await get_table_data(conn, table_name)
            schema = await get_table_schema(conn, table_name)
            
            table_backup = {
                "table_name": table_name,
                "schema": schema,
                "row_count": len(data),
                "data": data
            }
            
            file_path = os.path.join(backup_subfolder, f"{table_name}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(table_backup, f, cls=CustomJSONEncoder, indent=2, ensure_ascii=False)
            
            metadata["tables"].append({
                "table_name": table_name,
                "row_count": len(data),
                "file": f"{table_name}.json"
            })
            
            logger.info(f"  - Backed up {len(data)} rows")
        
        metadata_path = os.path.join(backup_subfolder, "_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        await conn.close()
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Backup completed successfully!")
        logger.info(f"Backup location: {backup_subfolder}")
        logger.info(f"Tables backed up: {len(tables)}")
        logger.info(f"{'='*50}")
        
        return backup_subfolder
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def list_available_backups(backup_folder: Optional[str] = None) -> list[str]:
    """
    Lists all available backup folders.
    """
    folder = backup_folder or DEFAULT_BACKUP_FOLDER
    
    if not os.path.exists(folder):
        return []
    
    backups = []
    for item in os.listdir(folder):
        item_path = os.path.join(folder, item)
        if os.path.isdir(item_path) and item.startswith("backup_"):
            metadata_path = os.path.join(item_path, "_metadata.json")
            if os.path.exists(metadata_path):
                backups.append(item)
    
    return sorted(backups, reverse=True)


def get_backup_tables(backup_path: str) -> list[dict]:
    """
    Gets the list of tables available in a backup.
    """
    metadata_path = os.path.join(backup_path, "_metadata.json")
    
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    return metadata.get("tables", [])


async def restore_table(conn: asyncpg.Connection, backup_path: str, table_name: str, clear_existing: bool = False):
    """
    Restores a single table from backup.
    """
    file_path = os.path.join(backup_path, f"{table_name}.json")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Backup file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        table_backup = json.load(f)
    
    data = table_backup.get("data", [])
    
    if not data:
        logger.info(f"No data to restore for table: {table_name}")
        return 0
    
    if clear_existing:
        await conn.execute(f'DELETE FROM "{table_name}"')
        logger.info(f"  - Cleared existing data from {table_name}")
    
    columns = list(data[0].keys())
    placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
    column_names = ', '.join([f'"{col}"' for col in columns])
    
    insert_query = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
    
    inserted_count = 0
    for row in data:
        values = []
        for col in columns:
            value = row.get(col)
            if value is not None:
                if col in ['created_at', 'updated_at', 'date', 'timestamp']:
                    if isinstance(value, str):
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            values.append(value)
        
        try:
            await conn.execute(insert_query, *values)
            inserted_count += 1
        except asyncpg.PostgresError as e:
            logger.warning(f"  - Skipped row due to error: {e}")
    
    return inserted_count


async def restore_database(backup_path: str, selected_tables: Optional[list[str]] = None, clear_existing: bool = False):
    """
    Restores tables from a backup with optional table selection.
    """
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup path not found: {backup_path}")
    
    available_tables = get_backup_tables(backup_path)
    available_table_names = [t['table_name'] for t in available_tables]
    
    if selected_tables:
        tables_to_restore = [t for t in selected_tables if t in available_table_names]
        invalid_tables = [t for t in selected_tables if t not in available_table_names]
        if invalid_tables:
            logger.warning(f"Tables not found in backup: {', '.join(invalid_tables)}")
    else:
        tables_to_restore = available_table_names
    
    if not tables_to_restore:
        logger.error("No valid tables to restore")
        return
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Connected to database successfully")
        
        logger.info(f"\nRestoring {len(tables_to_restore)} tables: {', '.join(tables_to_restore)}")
        
        results = {}
        for table_name in tables_to_restore:
            logger.info(f"Restoring table: {table_name}")
            try:
                count = await restore_table(conn, backup_path, table_name, clear_existing)
                results[table_name] = {"status": "success", "rows_restored": count}
                logger.info(f"  - Restored {count} rows")
            except Exception as e:
                results[table_name] = {"status": "error", "error": str(e)}
                logger.error(f"  - Error: {e}")
        
        await conn.close()
        
        logger.info(f"\n{'='*50}")
        logger.info("Restore completed!")
        logger.info(f"{'='*50}")
        
        for table_name, result in results.items():
            if result["status"] == "success":
                logger.info(f"  ✓ {table_name}: {result['rows_restored']} rows")
            else:
                logger.info(f"  ✗ {table_name}: {result['error']}")
        
        return results
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


async def drop_all_tables():
    """
    Drops all tables from the database. This is a destructive operation.
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Connected to database successfully")
        
        tables = await get_all_tables(conn)
        
        if not tables:
            logger.info("No tables found in the database.")
            await conn.close()
            return
        
        logger.info(f"\nDropping {len(tables)} tables: {', '.join(tables)}")
        
        for table_name in tables:
            logger.info(f"Dropping table: {table_name}")
            await conn.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
            logger.info(f"  - Dropped {table_name}")
        
        await conn.close()
        
        logger.info(f"\n{'='*50}")
        logger.info("All tables dropped successfully!")
        logger.info(f"{'='*50}")
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def interactive_drop_tables():
    """
    Interactive confirmation for dropping all tables.
    """
    print("\n" + "!"*60)
    print("    WARNING: This will DROP ALL TABLES from the database!")
    print("    This action is IRREVERSIBLE!")
    print("!"*60)
    
    confirm1 = input("\nAre you sure you want to drop all tables? (yes/no): ").strip().lower()
    if confirm1 != 'yes':
        print("Operation cancelled.")
        return False
    
    confirm2 = input("Type 'DROP ALL' to confirm: ").strip()
    if confirm2 != 'DROP ALL':
        print("Confirmation failed. Operation cancelled.")
        return False
    
    return True


def interactive_menu():
    """
    Interactive menu for backup and restore operations.
    """
    print("\n" + "="*60)
    print("         DATABASE BACKUP & RESTORE UTILITY")
    print("="*60)
    print("\n1. Backup Database (export all tables to JSON)")
    print("2. Restore Database (import from JSON backup)")
    print("3. List Available Backups")
    print("4. Drop All Tables (DANGEROUS)")
    print("5. Exit")
    print("\n" + "-"*60)
    
    choice = input("Enter your choice (1-5): ").strip()
    return choice


def interactive_restore():
    """
    Interactive restore process with table selection.
    """
    backups = list_available_backups()
    
    if not backups:
        print("\nNo backups found!")
        return None, None
    
    print("\nAvailable Backups:")
    print("-"*40)
    for i, backup in enumerate(backups, 1):
        backup_path = os.path.join(DEFAULT_BACKUP_FOLDER, backup)
        tables = get_backup_tables(backup_path)
        total_rows = sum(t.get('row_count', 0) for t in tables)
        print(f"  {i}. {backup} ({len(tables)} tables, {total_rows} rows)")
    
    print("-"*40)
    
    try:
        backup_choice = int(input("\nSelect backup number (0 to cancel): "))
        if backup_choice == 0:
            return None, None
        if backup_choice < 1 or backup_choice > len(backups):
            print("Invalid selection!")
            return None, None
    except ValueError:
        print("Invalid input!")
        return None, None
    
    selected_backup = backups[backup_choice - 1]
    backup_path = os.path.join(DEFAULT_BACKUP_FOLDER, selected_backup)
    
    tables = get_backup_tables(backup_path)
    
    print(f"\nTables in backup '{selected_backup}':")
    print("-"*40)
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table['table_name']} ({table['row_count']} rows)")
    print("-"*40)
    
    print("\nOptions:")
    print("  - Enter table numbers separated by commas (e.g., 1,3,4)")
    print("  - Enter 'all' to restore all tables")
    print("  - Enter 0 to cancel")
    
    table_input = input("\nSelect tables to restore: ").strip().lower()
    
    if table_input == '0' or table_input == '':
        return None, None
    
    if table_input == 'all':
        selected_tables = [t['table_name'] for t in tables]
    else:
        try:
            indices = [int(x.strip()) for x in table_input.split(',')]
            selected_tables = []
            for idx in indices:
                if 1 <= idx <= len(tables):
                    selected_tables.append(tables[idx - 1]['table_name'])
            
            if not selected_tables:
                print("No valid tables selected!")
                return None, None
        except ValueError:
            print("Invalid input!")
            return None, None
    
    clear_choice = input("\nClear existing data before restore? (y/N): ").strip().lower()
    clear_existing = clear_choice == 'y'
    
    print(f"\n{'='*40}")
    print("Restore Summary:")
    print(f"  Backup: {selected_backup}")
    print(f"  Tables: {', '.join(selected_tables)}")
    print(f"  Clear existing: {'Yes' if clear_existing else 'No'}")
    print(f"{'='*40}")
    
    confirm = input("\nProceed with restore? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Restore cancelled.")
        return None, None
    
    return backup_path, selected_tables, clear_existing


def main():
    """
    Main entry point for the script.
    """
    while True:
        choice = interactive_menu()
        
        if choice == '1':
            print("\nStarting database backup...")
            asyncio.run(backup_database())
            
        elif choice == '2':
            result = interactive_restore()
            if result and result[0]:
                backup_path, selected_tables, clear_existing = result
                asyncio.run(restore_database(backup_path, selected_tables, clear_existing))
            
        elif choice == '3':
            backups = list_available_backups()
            if backups:
                print("\nAvailable Backups:")
                print("-"*40)
                for backup in backups:
                    backup_path = os.path.join(DEFAULT_BACKUP_FOLDER, backup)
                    tables = get_backup_tables(backup_path)
                    total_rows = sum(t.get('row_count', 0) for t in tables)
                    print(f"  • {backup}")
                    print(f"    Tables: {len(tables)}, Total rows: {total_rows}")
                print("-"*40)
            else:
                print("\nNo backups found!")
            
        elif choice == '4':
            if interactive_drop_tables():
                asyncio.run(drop_all_tables())
            
        elif choice == '5':
            print("\nGoodbye!")
            break
            
        else:
            print("\nInvalid choice. Please try again.")


if __name__ == "__main__":
    main()
