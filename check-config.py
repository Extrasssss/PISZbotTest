#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

def check_config():
    print("🔍 Checking configuration...")
    
    config = {
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'SERVER_IP': os.getenv('SERVER_IP'),
        'DB_NAME': os.getenv('DB_NAME'),
        'SQL_LOGIN': os.getenv('SQL_LOGIN'),
        'SQL_PASSWORD': os.getenv('SQL_PASSWORD'),
        'ADMIN_IDS': os.getenv('ADMIN_IDS')
    }
    
    all_good = True
    
    for key, value in config.items():
        if not value or value.startswith('your_') or '***' in value:
            print(f"❌ {key}: NOT SET")
            all_good = False
        else:
            print(f"✅ {key}: Set")
    
    if all_good:
        print("\n🎉 Configuration is ready!")
    else:
        print("\n⚠️  Please complete the configuration in .env file")

if __name__ == "__main__":
    check_config()