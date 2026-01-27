#!/bin/bash
DATE=$(date +%Y-%m-%d_%H%M)
BACKUP_DIR="/opt/RealmQuest-Backups"
mkdir -p $BACKUP_DIR
echo "📦 Backing up RealmQuest Data..."
tar -czf "$BACKUP_DIR/rq_data_$DATE.tar.gz" -C /opt RealmQuest-Data
echo "✅ Backup saved to $BACKUP_DIR/rq_data_$DATE.tar.gz"
