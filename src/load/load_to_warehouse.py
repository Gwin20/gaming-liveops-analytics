"""
Load raw CSV data into DuckDB warehouse
"""
import duckdb
from pathlib import Path
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

def create_warehouse():
    print("\n" + "="*60)
    print("🏗️  BUILDING DATA WAREHOUSE")
    print("="*60 + "\n")
    
    warehouse_path = Path(config['paths']['warehouse'])
    warehouse_path.mkdir(parents=True, exist_ok=True)
    db_path = warehouse_path / 'gaming_analytics.duckdb'
    
    print(f"📦 Connecting to DuckDB: {db_path}")
    con = duckdb.connect(str(db_path))
    con.execute(f"SET memory_limit='{config['database']['memory_limit']}'")
    
    raw_path = Path(config['paths']['raw_data'])
    
    print("\n📥 Step 1/3: Loading raw data into staging tables...")
    
    con.execute("DROP TABLE IF EXISTS stg_players")
    con.execute("DROP TABLE IF EXISTS stg_sessions")
    con.execute("DROP TABLE IF EXISTS stg_purchases")
    
    con.execute(f"CREATE TABLE stg_players AS SELECT * FROM read_csv_auto('{raw_path}/players.csv')")
    print("   ✓ stg_players loaded")
    
    con.execute(f"CREATE TABLE stg_sessions AS SELECT * FROM read_csv_auto('{raw_path}/sessions.csv')")
    print("   ✓ stg_sessions loaded")
    
    con.execute(f"CREATE TABLE stg_purchases AS SELECT * FROM read_csv_auto('{raw_path}/purchases.csv')")
    print("   ✓ stg_purchases loaded")
    
    print("\n🔷 Step 2/3: Creating dimension tables...")
    
    con.execute("DROP TABLE IF EXISTS dim_players")
    con.execute("""
        CREATE TABLE dim_players AS
        SELECT 
            player_id,
            registration_date::DATE as registration_date,
            country, platform, install_source, device_type, player_level,
            CURRENT_TIMESTAMP as loaded_at
        FROM stg_players
    """)
    print("   ✓ dim_players created")
    
    print("\n📊 Step 3/3: Creating fact tables...")
    
    con.execute("DROP TABLE IF EXISTS fact_sessions")
    con.execute("""
        CREATE TABLE fact_sessions AS
        SELECT 
            session_id, player_id,
            session_start::TIMESTAMP as session_start,
            session_end::TIMESTAMP as session_end,
            duration_minutes, levels_completed, deaths, items_collected, score,
            DATE_TRUNC('day', session_start::TIMESTAMP) as session_date,
            CURRENT_TIMESTAMP as loaded_at
        FROM stg_sessions
    """)
    print("   ✓ fact_sessions created")
    
    con.execute("DROP TABLE IF EXISTS fact_purchases")
    con.execute("""
        CREATE TABLE fact_purchases AS
        SELECT 
            purchase_id, player_id, session_id,
            purchase_time::TIMESTAMP as purchase_time,
            item_type, item_name, price_usd, currency, platform,
            DATE_TRUNC('day', purchase_time::TIMESTAMP) as purchase_date,
            CURRENT_TIMESTAMP as loaded_at
        FROM stg_purchases
    """)
    print("   ✓ fact_purchases created")
    
    print("\n🔍 Creating indexes...")
    con.execute("CREATE INDEX idx_sessions_player ON fact_sessions(player_id)")
    con.execute("CREATE INDEX idx_sessions_date ON fact_sessions(session_date)")
    con.execute("CREATE INDEX idx_purchases_player ON fact_purchases(player_id)")
    con.execute("CREATE INDEX idx_purchases_date ON fact_purchases(purchase_date)")
    print("   ✓ Indexes created")
    
    print("\n✅ Data Validation:")
    players_count = con.execute("SELECT COUNT(*) FROM dim_players").fetchone()[0]
    sessions_count = con.execute("SELECT COUNT(*) FROM fact_sessions").fetchone()[0]
    purchases_count = con.execute("SELECT COUNT(*) FROM fact_purchases").fetchone()[0]
    total_revenue = con.execute("SELECT SUM(price_usd) FROM fact_purchases").fetchone()[0] or 0
    avg_session = con.execute("SELECT AVG(duration_minutes) FROM fact_sessions").fetchone()[0] or 0
    
    print(f"   Players:   {players_count:,}")
    print(f"   Sessions:  {sessions_count:,}")
    print(f"   Purchases: {purchases_count:,}")
    print(f"\n📈 Quick Stats:")
    print(f"   Total Revenue:        ${total_revenue:,.2f}")
    print(f"   Avg Session Duration: {avg_session:.1f} minutes")
    
    con.close()
    print("\n" + "="*60)
    print("✅ WAREHOUSE BUILD COMPLETE!")
    print("="*60 + "\n")

if __name__ == "__main__":
    create_warehouse()
