"""
Check what tables and data exist in the database
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_database():
    database_url = os.getenv("DATABASE_URL")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # List all tables
        print("\n=== Tables in Database ===")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        for table in tables:
            table_name = table['table_name']
            print(f"\nTable: {table_name}")
            
            # Count rows
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"  Rows: {count}")
            
            # Show columns
            columns = await conn.fetch(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                LIMIT 10
            """)
            print(f"  Columns ({len(columns)}):")
            for col in columns[:5]:
                print(f"    - {col['column_name']} ({col['data_type']})")
            if len(columns) > 5:
                print(f"    ... and {len(columns) - 5} more")
        
        if not tables:
            print("No tables found in database!")
            print("\nThe database is empty. You have two options:")
            print("1. Upload CSV files through the UI (Upload CSV button)")
            print("2. Create and populate the 'superstore' table in your Neon database")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_database())
