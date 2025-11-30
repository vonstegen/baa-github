"""
Extension Bridge - Connects F-Agent to Seller Central Extension

This module provides the interface between the F-Agent and the 
BAA Seller Central browser extension for eligibility checking.

Integration Methods:
1. File-based: Extension exports to JSON, F-Agent reads
2. WebSocket: Real-time bidirectional communication
3. Native Messaging: Firefox native messaging API

Currently implements: File-based (simplest for MVP)
"""

import json
import sqlite3
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from datetime import datetime, timedelta


class EligibilityStatus(Enum):
    GOOD = "GOOD"
    NEED_APPROVAL = "NEED_APPROVAL"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"
    NOT_CHECKED = "NOT_CHECKED"


@dataclass
class EligibilityResult:
    asin: str
    status: EligibilityStatus
    condition: str
    checked_at: datetime
    bsr: Optional[int] = None
    title: Optional[str] = None
    message: Optional[str] = None
    
    def is_sellable(self) -> bool:
        """Can we sell this product?"""
        return self.status == EligibilityStatus.GOOD
    
    def needs_approval(self) -> bool:
        """Do we need to apply for approval?"""
        return self.status == EligibilityStatus.NEED_APPROVAL
    
    def is_restricted(self) -> bool:
        """Is this product restricted?"""
        return self.status == EligibilityStatus.RESTRICTED
    
    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Is this result too old?"""
        # Handle timezone-aware and naive datetimes
        now = datetime.now()
        checked = self.checked_at
        
        # If checked_at is timezone-aware, make it naive for comparison
        if checked.tzinfo is not None:
            checked = checked.replace(tzinfo=None)
        
        age = now - checked
        return age > timedelta(hours=max_age_hours)


class EligibilityCache:
    """SQLite cache for eligibility results"""
    
    def __init__(self, db_path: str = "data/eligibility_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS eligibility (
                    asin TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    condition TEXT,
                    bsr INTEGER,
                    title TEXT,
                    message TEXT,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checked_at 
                ON eligibility(checked_at)
            """)
    
    def get(self, asin: str) -> Optional[EligibilityResult]:
        """Get cached eligibility result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM eligibility WHERE asin = ?", 
                (asin,)
            ).fetchone()
            
            if row:
                return EligibilityResult(
                    asin=row['asin'],
                    status=EligibilityStatus(row['status']),
                    condition=row['condition'] or 'Used',
                    checked_at=datetime.fromisoformat(row['checked_at']),
                    bsr=row['bsr'],
                    title=row['title'],
                    message=row['message']
                )
        return None
    
    def set(self, result: EligibilityResult):
        """Cache eligibility result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO eligibility 
                (asin, status, condition, bsr, title, message, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.asin,
                result.status.value,
                result.condition,
                result.bsr,
                result.title,
                result.message,
                result.checked_at.isoformat()
            ))
    
    def get_batch(self, asins: List[str]) -> dict:
        """Get multiple eligibility results"""
        results = {}
        for asin in asins:
            result = self.get(asin)
            if result:
                results[asin] = result
        return results
    
    def cleanup_old(self, max_age_days: int = 7):
        """Remove old entries"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM eligibility WHERE checked_at < ?",
                (cutoff.isoformat(),)
            )


class ExtensionBridge:
    """
    Bridge between F-Agent and Seller Central Extension
    
    The extension saves results to browser storage. This bridge
    reads from exported JSON files or can trigger checks via
    automation.
    """
    
    def __init__(
        self, 
        export_path: str = "data/extension_export.json",
        cache_db: str = "data/eligibility_cache.db"
    ):
        self.export_path = Path(export_path)
        self.cache = EligibilityCache(cache_db)
        
    def import_from_extension(self, filepath: str = None) -> List[EligibilityResult]:
        """
        Import results from extension's exported JSON file.
        
        Extension exports data in format:
        {
            "exportedAt": "2025-11-29T20:00:00Z",
            "version": "6.2",
            "source": "baa-seller-central-extension",
            "results": [
                {
                    "asin": "1234567890",
                    "status": "GOOD",
                    "condition": "Used",
                    "bsr": 150000,
                    "title": "Book Title",
                    "checkedAt": "2025-11-29T19:00:00Z"
                },
                ...
            ]
        }
        
        Args:
            filepath: Path to JSON file. If None, uses default export_path.
        
        Returns:
            List of EligibilityResult objects
        """
        import_path = Path(filepath) if filepath else self.export_path
        
        if not import_path.exists():
            print(f"Export file not found: {import_path}")
            print("Tip: Use the extension's 'Export JSON (F-Agent)' button")
            return []
        
        with open(import_path) as f:
            data = json.load(f)
        
        print(f"Importing from: {import_path}")
        print(f"Export version: {data.get('version', 'unknown')}")
        print(f"Exported at: {data.get('exportedAt', 'unknown')}")
        
        results = []
        for item in data.get('results', []):
            # Parse timestamp - handle both Z and +00:00 formats
            checked_at_str = item.get('checkedAt', '')
            try:
                if checked_at_str.endswith('Z'):
                    checked_at = datetime.fromisoformat(checked_at_str.replace('Z', '+00:00'))
                else:
                    checked_at = datetime.fromisoformat(checked_at_str)
            except:
                checked_at = datetime.now()
            
            result = EligibilityResult(
                asin=item['asin'],
                status=EligibilityStatus(item['status']),
                condition=item.get('condition', 'Used'),
                checked_at=checked_at,
                bsr=item.get('bsr'),
                title=item.get('title'),
                message=item.get('message')
            )
            results.append(result)
            self.cache.set(result)  # Cache imported results
        
        print(f"Imported {len(results)} eligibility results")
        return results
    
    def check_eligibility(
        self, 
        asin: str, 
        use_cache: bool = True,
        max_cache_age_hours: int = 24
    ) -> EligibilityResult:
        """
        Check eligibility for a single ASIN.
        
        First checks cache, then falls back to extension check.
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get(asin)
            if cached and not cached.is_stale(max_cache_age_hours):
                return cached
        
        # Not in cache or stale - need to trigger extension check
        # For now, return NOT_CHECKED status
        # TODO: Implement browser automation to trigger check
        return EligibilityResult(
            asin=asin,
            status=EligibilityStatus.NOT_CHECKED,
            condition='Unknown',
            checked_at=datetime.now(),
            message='Not in cache - manual check required'
        )
    
    def check_batch(
        self, 
        asins: List[str],
        use_cache: bool = True
    ) -> dict:
        """
        Check eligibility for multiple ASINs.
        
        Returns dict mapping ASIN to EligibilityResult.
        """
        results = {}
        uncached = []
        
        if use_cache:
            cached = self.cache.get_batch(asins)
            for asin, result in cached.items():
                if not result.is_stale():
                    results[asin] = result
                else:
                    uncached.append(asin)
            uncached.extend([a for a in asins if a not in cached])
        else:
            uncached = asins
        
        # For uncached ASINs, return NOT_CHECKED
        # TODO: Implement batch checking via automation
        for asin in uncached:
            results[asin] = EligibilityResult(
                asin=asin,
                status=EligibilityStatus.NOT_CHECKED,
                condition='Unknown',
                checked_at=datetime.now(),
                message='Not in cache - manual check required'
            )
        
        return results
    
    def get_statistics(self) -> dict:
        """Get cache statistics"""
        with sqlite3.connect(self.cache.db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM eligibility"
            ).fetchone()[0]
            
            by_status = {}
            for status in EligibilityStatus:
                count = conn.execute(
                    "SELECT COUNT(*) FROM eligibility WHERE status = ?",
                    (status.value,)
                ).fetchone()[0]
                by_status[status.value] = count
            
            recent = conn.execute("""
                SELECT COUNT(*) FROM eligibility 
                WHERE checked_at > datetime('now', '-24 hours')
            """).fetchone()[0]
        
        return {
            'total_cached': total,
            'by_status': by_status,
            'checked_last_24h': recent
        }


# Example usage
if __name__ == "__main__":
    bridge = ExtensionBridge()
    
    # Import from extension export
    results = bridge.import_from_extension()
    print(f"Imported {len(results)} results from extension")
    
    # Check single ASIN
    result = bridge.check_eligibility("1234567890")
    print(f"ASIN 1234567890: {result.status.value}")
    
    # Check batch
    asins = ["1111111111", "2222222222", "3333333333"]
    batch_results = bridge.check_batch(asins)
    for asin, result in batch_results.items():
        print(f"{asin}: {result.status.value}")
    
    # Get stats
    stats = bridge.get_statistics()
    print(f"Cache stats: {stats}")
