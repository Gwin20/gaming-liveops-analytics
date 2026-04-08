"""
Generate synthetic gaming events data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
import random
from pathlib import Path
import yaml

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

def generate_players(n_players, start_date):
    """Generate player dimension data"""
    print(f"   Generating {n_players} players...")
    players = []
    
    for i in range(n_players):
        # Register players BEFORE or during the simulation period
        days_before_start = random.randint(0, 365)
        reg_date = start_date - timedelta(days=days_before_start)
        
        players.append({
            'player_id': f'P{i:06d}',
            'registration_date': reg_date,
            'country': fake.country_code(),
            'platform': random.choice(['iOS', 'Android', 'Web']),
            'install_source': random.choice(['organic', 'facebook', 'google', 'tiktok', 'instagram']),
            'device_type': random.choice(['mobile', 'tablet', 'desktop']),
            'player_level': 1
        })
    
    return pd.DataFrame(players)


def generate_sessions(players_df, n_days, start_date):
    """Generate session events"""
    print(f"   Generating sessions for {n_days} days...")
    sessions = []
    
    for idx, player in players_df.iterrows():
        if idx % 500 == 0:
            print(f"      Processing player {idx}/{len(players_df)}...")
            
        reg_date = pd.to_datetime(player['registration_date'])
        
        # Each player has different engagement levels
        engagement_level = random.choice(['high', 'medium', 'low'])
        play_probability = {'high': 0.7, 'medium': 0.4, 'low': 0.15}[engagement_level]
        
        # Determine when player churns
        active_days = random.randint(1, n_days)
        
        for day in range(n_days):
            current_date = start_date + timedelta(days=day)
            
            # Skip if before registration
            if current_date < reg_date:
                continue
            
            # Player churned
            if day > active_days:
                break
            
            # Daily play probability based on engagement
            if random.random() > play_probability:
                continue
            
            # Sessions per day
            sessions_today = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
            
            for session_num in range(sessions_today):
                session_start = current_date + timedelta(
                    hours=random.randint(6, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                # Session duration
                duration_minutes = max(1, min(int(np.random.exponential(20)), 180))
                
                sessions.append({
                    'session_id': f'S{len(sessions):08d}',
                    'player_id': player['player_id'],
                    'session_start': session_start,
                    'session_end': session_start + timedelta(minutes=duration_minutes),
                    'duration_minutes': duration_minutes,
                    'levels_completed': random.randint(0, 5),
                    'deaths': random.randint(0, 10),
                    'items_collected': random.randint(5, 50),
                    'score': random.randint(100, 10000)
                })
    
    return pd.DataFrame(sessions)


def generate_purchases(sessions_df, players_df):
    """Generate in-app purchase events"""
    print(f"   Generating purchases...")
    
    if len(sessions_df) == 0:
        print("      ⚠️  No sessions to generate purchases from!")
        return pd.DataFrame(columns=[
            'purchase_id', 'player_id', 'session_id', 'purchase_time',
            'item_type', 'item_name', 'price_usd', 'currency', 'platform'
        ])
    
    purchases = []
    
    # 5% of players are payers
    paying_players = players_df.sample(frac=0.05)['player_id'].tolist()
    
    print(f"      Paying players: {len(paying_players)}")
    
    for idx, session in sessions_df.iterrows():
        if session['player_id'] not in paying_players:
            continue
        
        # 10% chance of purchase per session for payers
        if random.random() < 0.10:
            purchase_time = session['session_start'] + timedelta(
                minutes=random.randint(0, int(session['duration_minutes']))
            )
            
            item_type = random.choice(['currency', 'powerup', 'cosmetic', 'bundle'])
            
            price_map = {
                'currency': [0.99, 4.99, 9.99, 19.99],
                'powerup': [0.99, 1.99, 2.99],
                'cosmetic': [2.99, 4.99, 7.99],
                'bundle': [9.99, 19.99, 49.99]
            }
            
            purchases.append({
                'purchase_id': f'PUR{len(purchases):08d}',
                'player_id': session['player_id'],
                'session_id': session['session_id'],
                'purchase_time': purchase_time,
                'item_type': item_type,
                'item_name': f'{item_type}_{random.randint(1, 20)}',
                'price_usd': random.choice(price_map[item_type]),
                'currency': 'USD',
                'platform': random.choice(['iOS', 'Android', 'Web'])
            })
    
    if len(purchases) == 0:
        print("      ⚠️  No purchases generated")
        return pd.DataFrame(columns=[
            'purchase_id', 'player_id', 'session_id', 'purchase_time',
            'item_type', 'item_name', 'price_usd', 'currency', 'platform'
        ])
    
    return pd.DataFrame(purchases)


def main():
    print("\n" + "="*60)
    print("🎮 GAMING ANALYTICS DATA GENERATOR")
    print("="*60 + "\n")
    
    n_players = config['simulation']['n_players']
    n_days = config['simulation']['n_days']
    start_date = datetime.strptime(config['simulation']['start_date'], '%Y-%m-%d')
    
    print(f"Simulation period: {start_date.date()} to {(start_date + timedelta(days=n_days)).date()}")
    print()
    
    # Generate data
    print("📊 Step 1/3: Generating Players")
    players_df = generate_players(n_players, start_date)
    
    print("\n🎯 Step 2/3: Generating Sessions")
    sessions_df = generate_sessions(players_df, n_days, start_date)
    
    print("\n💰 Step 3/3: Generating Purchases")
    purchases_df = generate_purchases(sessions_df, players_df)
    
    # Save to raw data folder
    print("\n💾 Saving data to CSV...")
    raw_path = Path(config['paths']['raw_data'])
    raw_path.mkdir(parents=True, exist_ok=True)
    
    players_df.to_csv(raw_path / 'players.csv', index=False)
    sessions_df.to_csv(raw_path / 'sessions.csv', index=False)
    purchases_df.to_csv(raw_path / 'purchases.csv', index=False)
    
    # Calculate metrics
    if len(purchases_df) > 0:
        total_revenue = purchases_df['price_usd'].sum()
        paying_users = purchases_df['player_id'].nunique()
        arppu = total_revenue / paying_users if paying_users > 0 else 0
    else:
        total_revenue = 0
        paying_users = 0
        arppu = 0
    
    print("\n" + "="*60)
    print("✅ DATA GENERATION COMPLETE!")
    print("="*60)
    print(f"   👥 Players:        {len(players_df):,}")
    print(f"   🎮 Sessions:       {len(sessions_df):,}")
    print(f"   💳 Purchases:      {len(purchases_df):,}")
    print(f"   💰 Total Revenue:  ${total_revenue:,.2f}")
    print(f"   🐋 Paying Users:   {paying_users:,} ({paying_users/len(players_df)*100:.1f}%)")
    if paying_users > 0:
        print(f"   📊 ARPPU:          ${arppu:.2f}")
    print("="*60 + "\n")
    
    # Data quality check
    if len(sessions_df) == 0:
        print("⚠️  WARNING: No sessions generated! Check date logic.")
    if len(purchases_df) == 0:
        print("⚠️  WARNING: No purchases generated!")
    
    print("📁 Files saved to:")
    print(f"   - {raw_path / 'players.csv'}")
    print(f"   - {raw_path / 'sessions.csv'}")
    print(f"   - {raw_path / 'purchases.csv'}")
    print()


if __name__ == "__main__":
    main()
