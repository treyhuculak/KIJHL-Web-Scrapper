"""
Firebase Data Migration Script
Migrates existing KIJHL data from flat structure to multi-league structure.

Old structure:
- officials/
- games/

New structure:
- leagues/kijhl/officials/
- leagues/kijhl/games/

Usage:
    python migrate_to_multi_league.py --dry-run         # Preview changes without migrating
    python migrate_to_multi_league.py --migrate         # Perform migration
    python migrate_to_multi_league.py --verify          # Verify migration succeeded
    python migrate_to_multi_league.py --cleanup         # Delete old collections after verification
"""

import firebase_admin
from firebase_admin import credentials, firestore
import argparse
import sys
from datetime import datetime

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def count_documents(collection_path):
    """Count documents in a collection."""
    try:
        docs = db.collection(collection_path).stream()
        count = sum(1 for _ in docs)
        return count
    except Exception as e:
        print(f"❌ Error counting {collection_path}: {e}")
        return 0

def dry_run():
    """Preview what will be migrated without making changes."""
    print("\n" + "="*70)
    print("🔍 DRY RUN MODE - No changes will be made")
    print("="*70 + "\n")
    
    # Count old structure
    old_officials_count = count_documents('officials')
    old_games_count = count_documents('games')
    
    # Count new structure (if exists)
    new_officials_count = count_documents('leagues/kijhl/officials')
    new_games_count = count_documents('leagues/kijhl/games')
    
    print("📊 Current State:")
    print(f"  Old Structure:")
    print(f"    - officials/: {old_officials_count} documents")
    print(f"    - games/: {old_games_count} documents")
    print(f"\n  New Structure:")
    print(f"    - leagues/kijhl/officials/: {new_officials_count} documents")
    print(f"    - leagues/kijhl/games/: {new_games_count} documents")
    
    print(f"\n📦 Migration Plan:")
    print(f"  Will copy {old_officials_count} officials → leagues/kijhl/officials/")
    print(f"  Will copy {old_games_count} games → leagues/kijhl/games/")
    
    if new_officials_count > 0 or new_games_count > 0:
        print(f"\n⚠️  WARNING: New collections already contain data!")
        print(f"   This migration will ADD to existing data (won't overwrite).")
    
    print(f"\n✅ To perform migration, run: python migrate_to_multi_league.py --migrate")

def migrate_collection(source_path, dest_path, batch_size=500):
    """Migrate all documents from source to destination collection.
    
    Args:
        source_path: Source collection path (e.g., 'officials')
        dest_path: Destination collection path (e.g., 'leagues/kijhl/officials')
        batch_size: Number of documents to process in each batch
    """
    print(f"\n🔄 Migrating: {source_path} → {dest_path}")
    
    # Get all documents from source
    source_docs = db.collection(source_path).stream()
    
    migrated = 0
    skipped = 0
    errors = 0
    batch = db.batch()
    batch_count = 0
    
    for doc in source_docs:
        try:
            # Check if document already exists in destination
            dest_ref = db.collection(dest_path).document(doc.id)
            if dest_ref.get().exists:
                skipped += 1
                print(f"  ⏭️  Skipping {doc.id} (already exists)")
                continue
            
            # Add to batch
            batch.set(dest_ref, doc.to_dict())
            batch_count += 1
            migrated += 1
            
            # Commit batch when it reaches batch_size
            if batch_count >= batch_size:
                batch.commit()
                print(f"  ✅ Committed batch of {batch_count} documents")
                batch = db.batch()
                batch_count = 0
                
        except Exception as e:
            errors += 1
            print(f"  ❌ Error migrating {doc.id}: {e}")
    
    # Commit any remaining documents
    if batch_count > 0:
        batch.commit()
        print(f"  ✅ Committed final batch of {batch_count} documents")
    
    print(f"\n📊 Migration Summary for {source_path}:")
    print(f"  ✅ Migrated: {migrated}")
    print(f"  ⏭️  Skipped: {skipped}")
    print(f"  ❌ Errors: {errors}")
    
    return migrated, skipped, errors

def migrate():
    """Perform the full migration."""
    print("\n" + "="*70)
    print("🚀 MIGRATION MODE - Migrating data to new structure")
    print("="*70)
    
    start_time = datetime.now()
    
    # Migrate officials
    officials_migrated, officials_skipped, officials_errors = migrate_collection(
        'officials',
        'leagues/kijhl/officials'
    )
    
    # Migrate games
    games_migrated, games_skipped, games_errors = migrate_collection(
        'games',
        'leagues/kijhl/games'
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*70)
    print("🎉 MIGRATION COMPLETE")
    print("="*70)
    print(f"\n📊 Overall Summary:")
    print(f"  Officials:")
    print(f"    ✅ Migrated: {officials_migrated}")
    print(f"    ⏭️  Skipped: {officials_skipped}")
    print(f"    ❌ Errors: {officials_errors}")
    print(f"\n  Games:")
    print(f"    ✅ Migrated: {games_migrated}")
    print(f"    ⏭️  Skipped: {games_skipped}")
    print(f"    ❌ Errors: {games_errors}")
    print(f"\n⏱️  Duration: {duration:.2f} seconds")
    
    print(f"\n✅ Next steps:")
    print(f"  1. Run verification: python migrate_to_multi_league.py --verify")
    print(f"  2. Test your app to ensure it works with new structure")
    print(f"  3. If everything works, cleanup old data: python migrate_to_multi_league.py --cleanup")

def verify():
    """Verify that migration succeeded by comparing counts."""
    print("\n" + "="*70)
    print("✅ VERIFICATION MODE - Checking migration results")
    print("="*70 + "\n")
    
    # Count documents in both structures
    old_officials = count_documents('officials')
    old_games = count_documents('games')
    new_officials = count_documents('leagues/kijhl/officials')
    new_games = count_documents('leagues/kijhl/games')
    
    print("📊 Document Counts:")
    print(f"\n  Officials:")
    print(f"    Old (officials/): {old_officials}")
    print(f"    New (leagues/kijhl/officials/): {new_officials}")
    
    if old_officials == new_officials:
        print(f"    ✅ Counts match!")
    else:
        print(f"    ⚠️  Counts don't match (difference: {abs(old_officials - new_officials)})")
    
    print(f"\n  Games:")
    print(f"    Old (games/): {old_games}")
    print(f"    New (leagues/kijhl/games/): {new_games}")
    
    if old_games == new_games:
        print(f"    ✅ Counts match!")
    else:
        print(f"    ⚠️  Counts don't match (difference: {abs(old_games - new_games)})")
    
    # Overall verification
    if old_officials == new_officials and old_games == new_games:
        print(f"\n🎉 VERIFICATION PASSED - All data migrated successfully!")
        print(f"\n✅ Safe to proceed with cleanup: python migrate_to_multi_league.py --cleanup")
    else:
        print(f"\n⚠️  VERIFICATION INCOMPLETE - Some data may not have migrated")
        print(f"   Please investigate before proceeding with cleanup")

def cleanup():
    """Delete old collections after verification."""
    print("\n" + "="*70)
    print("🗑️  CLEANUP MODE - Deleting old collections")
    print("="*70 + "\n")
    
    print("⚠️  WARNING: This will permanently delete old collections!")
    print(f"  - officials/")
    print(f"  - games/")
    
    response = input("\n⚠️  Are you sure you want to proceed? (type 'yes' to confirm): ")
    
    if response.lower() != 'yes':
        print("❌ Cleanup cancelled")
        return
    
    print("\n🗑️  Deleting old collections...")
    
    # Delete officials
    print("  Deleting officials/...")
    deleted_officials = delete_collection('officials', batch_size=500)
    
    # Delete games
    print("  Deleting games/...")
    deleted_games = delete_collection('games', batch_size=500)
    
    print("\n" + "="*70)
    print("✅ CLEANUP COMPLETE")
    print("="*70)
    print(f"\n  Deleted {deleted_officials} officials")
    print(f"  Deleted {deleted_games} games")
    print(f"\n🎉 Your Firebase now uses the new multi-league structure!")

def delete_collection(collection_path, batch_size=500):
    """Delete all documents in a collection."""
    deleted = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        docs = db.collection(collection_path).limit(batch_size).stream()
        batch = db.batch()
        batch_count = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            batch_count += 1
            deleted += 1
        
        if batch_count == 0:
            # No more documents to delete
            break
        
        batch.commit()
        print(f"  ✅ Batch {batch_num}: Deleted {batch_count} documents (Total: {deleted})")
    
    return deleted

def main():
    parser = argparse.ArgumentParser(
        description='Migrate Firebase data from flat to multi-league structure'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview migration without making changes'
    )
    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Perform the migration'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration succeeded'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Delete old collections after verification'
    )
    
    args = parser.parse_args()
    
    # Check that exactly one argument is provided
    if not (args.dry_run or args.migrate or args.verify or args.cleanup):
        parser.print_help()
        sys.exit(1)
    
    if args.dry_run:
        dry_run()
    elif args.migrate:
        migrate()
    elif args.verify:
        verify()
    elif args.cleanup:
        cleanup()

if __name__ == '__main__':
    main()
