"""
Upload data.csv to Neon PostgreSQL database.
Run: python upload_data.py
"""

import asyncio
import asyncpg
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

async def upload_csv_to_db():
    """Upload CSV data to PostgreSQL database."""
    
    # Load CSV (handle different encodings)
    print("Loading data.csv...")
    try:
        df = pd.read_csv('data/data.csv', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv('data/data.csv', encoding='latin-1')
    print(f"Loaded {len(df)} rows")
    
    # Clean column names (lowercase, replace spaces/hyphens with underscores)
    df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')
    print(f"Columns: {list(df.columns)}")
    
    # Connect to database
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in .env file")
        return
    
    # Remove channel_binding parameter if present (Windows compatibility)
    database_url = database_url.replace('&channel_binding=require', '').replace('channel_binding=require&', '')
    
    print("Connecting to Neon database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Clear existing data in superstore table
        await conn.execute("TRUNCATE TABLE superstore;")
        print("✓ Cleared existing data from superstore table")
        
        # Convert dates
        df['order_date'] = pd.to_datetime(df['order_date'])
        df['ship_date'] = pd.to_datetime(df['ship_date'])
        
        # Insert data in batches
        print("Inserting data...")
        batch_size = 500
        total_inserted = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Prepare values for batch insert
            values = [
                (
                    int(row['row_id']),
                    str(row['order_id']),
                    row['order_date'],
                    row['ship_date'],
                    str(row['ship_mode']),
                    str(row['customer_id']),
                    str(row['customer_name']),
                    str(row['segment']),
                    str(row['country']),
                    str(row['city']),
                    str(row['state']),
                    str(row['postal_code']),
                    str(row['region']),
                    str(row['product_id']),
                    str(row['category']),
                    str(row['sub_category']),
                    str(row['product_name']),
                    float(row['sales']),
                    int(row['quantity']),
                    float(row['discount']),
                    float(row['profit'])
                )
                for _, row in batch.iterrows()
            ]
            
            await conn.executemany(
                """
                INSERT INTO superstore VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                )
                """,
                values
            )
            
            total_inserted += len(batch)
            print(f"  Inserted {total_inserted}/{len(df)} rows...")
        
        # Verify
        count = await conn.fetchval("SELECT COUNT(*) FROM superstore;")
        print(f"\n SUCCESS! {count} rows uploaded to superstore table")
        
        # Show sample
        sample = await conn.fetch("SELECT * FROM superstore LIMIT 3;")
        print("\nSample data:")
        for row in sample:
            print(f"  {dict(row)}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(upload_csv_to_db())
