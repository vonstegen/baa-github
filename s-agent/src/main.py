"""
S-Agent: Shipping & Status Agent

Main orchestrator for tracking books through the arbitrage pipeline.

Usage:
    from s_agent import SAgent
    
    agent = SAgent()
    book = agent.add_book(asin="1234567890", ...)
    agent.update_status(book.id, BookStatus.RECEIVED)
    dashboard = agent.get_dashboard()
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

from models.status import BookStatus, get_status_display
from models.book import Book


@dataclass
class DashboardData:
    """Dashboard summary data"""
    total_books: int
    active_books: int
    by_status: Dict[str, int]
    total_invested: float
    total_revenue: float
    total_profit: float
    total_sold: int
    average_roi: float
    average_days_to_sell: float
    books_needing_attention: int


class SAgent:
    """
    S-Agent: Shipping & Status Agent
    
    Tracks books through the entire arbitrage lifecycle.
    """
    
    def __init__(self, db_path: str = "data/inventory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory book storage (would use DB in production)
        self._books: Dict[str, Book] = {}
        
        # Event handlers
        self._status_handlers: List[Callable] = []
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    asin TEXT,
                    data TEXT,
                    status TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON books(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_asin ON books(asin)
            """)
    
    # -------------------------------------------------------------------------
    # Book Management
    # -------------------------------------------------------------------------
    
    def add_book(
        self,
        asin: str,
        title: str = "",
        source_marketplace: str = "",
        source_order_id: str = "",
        source_price: float = 0.0,
        source_shipping: float = 0.0,
        expected_condition: str = "",
        **kwargs
    ) -> Book:
        """
        Add a new book to tracking (typically called by B-Agent after purchase)
        """
        book = Book(
            asin=asin,
            title=title,
            source_marketplace=source_marketplace,
            source_order_id=source_order_id,
            source_price=source_price,
            source_shipping=source_shipping,
            expected_condition=expected_condition,
            ordered_at=datetime.now()
        )
        
        # Set any additional fields
        for key, value in kwargs.items():
            if hasattr(book, key):
                setattr(book, key, value)
        
        # Set initial status
        book.update_status(BookStatus.ORDERED, source="b-agent", notes="Order placed")
        
        # Store
        self._books[book.id] = book
        self._save_book(book)
        
        return book
    
    def get_book(self, book_id: str) -> Optional[Book]:
        """Get book by ID"""
        return self._books.get(book_id)
    
    def get_book_by_asin(self, asin: str) -> List[Book]:
        """Get all books with given ASIN"""
        return [b for b in self._books.values() if b.asin == asin]
    
    def get_book_by_order(self, source_order_id: str) -> Optional[Book]:
        """Get book by source order ID"""
        for book in self._books.values():
            if book.source_order_id == source_order_id:
                return book
        return None
    
    # -------------------------------------------------------------------------
    # Status Updates
    # -------------------------------------------------------------------------
    
    def update_status(
        self,
        book_id: str,
        new_status: BookStatus,
        source: str = "manual",
        notes: str = "",
        metadata: dict = None
    ) -> Book:
        """Update book status"""
        book = self.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        old_status = book.status
        book.update_status(new_status, source=source, notes=notes, metadata=metadata)
        
        self._save_book(book)
        self._emit_status_change(book, old_status, new_status)
        
        return book
    
    def mark_shipped_to_you(
        self,
        book_id: str,
        tracking: str,
        carrier: str = ""
    ) -> Book:
        """Mark book as shipped from source"""
        book = self.get_book(book_id)
        book.source_tracking = tracking
        book.source_carrier = carrier
        
        return self.update_status(
            book_id,
            BookStatus.SHIPPED_TO_YOU,
            source="tracking",
            metadata={'tracking': tracking, 'carrier': carrier}
        )
    
    def mark_received(
        self,
        book_id: str,
        actual_condition: str = "",
        notes: str = ""
    ) -> Book:
        """Mark book as received at your location"""
        book = self.get_book(book_id)
        if actual_condition:
            book.actual_condition = actual_condition
        if notes:
            book.condition_notes = notes
        
        return self.update_status(
            book_id,
            BookStatus.RECEIVED,
            source="manual",
            notes=notes
        )
    
    def mark_processed(
        self,
        book_id: str,
        condition: str,
        listing_price: float,
        fnsku: str = "",
        listing_notes: str = ""
    ) -> Book:
        """Mark book as processed and ready for FBA (called by L-Agent)"""
        book = self.get_book(book_id)
        book.listing_condition = condition
        book.listing_price = listing_price
        book.fnsku = fnsku
        book.listing_notes = listing_notes
        book.listed_at = datetime.now()
        
        return self.update_status(
            book_id,
            BookStatus.PROCESSED,
            source="l-agent"
        )
    
    def add_to_shipment(
        self,
        book_id: str,
        shipment_id: str,
        tracking: str = "",
        carrier: str = ""
    ) -> Book:
        """Add book to FBA shipment"""
        book = self.get_book(book_id)
        book.fba_shipment_id = shipment_id
        book.fba_tracking = tracking
        book.fba_carrier = carrier
        
        return self.update_status(
            book_id,
            BookStatus.FBA_SHIPMENT_CREATED,
            source="l-agent",
            metadata={'shipment_id': shipment_id}
        )
    
    def mark_fba_shipped(self, book_id: str, tracking: str = "") -> Book:
        """Mark FBA shipment as shipped"""
        book = self.get_book(book_id)
        if tracking:
            book.fba_tracking = tracking
        
        return self.update_status(
            book_id,
            BookStatus.FBA_SHIPPED,
            source="manual"
        )
    
    def mark_available(self, book_id: str) -> Book:
        """Mark book as available for sale on Amazon"""
        return self.update_status(
            book_id,
            BookStatus.FBA_AVAILABLE,
            source="sp-api"
        )
    
    def mark_sold(
        self,
        book_id: str,
        sale_order_id: str,
        sale_price: float,
        referral_fee: float = 0.0,
        fba_fee: float = 0.0
    ) -> Book:
        """Mark book as sold"""
        book = self.get_book(book_id)
        book.sale_order_id = sale_order_id
        book.sale_price = sale_price
        book.sale_date = datetime.now()
        book.referral_fee = referral_fee
        book.fba_fee = fba_fee
        
        return self.update_status(
            book_id,
            BookStatus.SOLD,
            source="sp-api",
            metadata={'order_id': sale_order_id, 'price': sale_price}
        )
    
    def mark_complete(self, book_id: str) -> Book:
        """Mark book lifecycle as complete"""
        return self.update_status(
            book_id,
            BookStatus.COMPLETE,
            source="s-agent"
        )
    
    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------
    
    def get_books_by_status(self, status: BookStatus) -> List[Book]:
        """Get all books with given status"""
        return [b for b in self._books.values() if b.status == status]
    
    def get_active_books(self) -> List[Book]:
        """Get all active (non-complete) books"""
        return [b for b in self._books.values() if b.is_active]
    
    def get_sellable_books(self) -> List[Book]:
        """Get all books currently available for sale"""
        return [b for b in self._books.values() if b.is_sellable]
    
    def get_books_needing_attention(self) -> List[Book]:
        """Get books that need attention"""
        return [b for b in self._books.values() if b.needs_attention]
    
    def get_books_in_transit(self) -> List[Book]:
        """Get all books currently in transit"""
        return [b for b in self._books.values() if b.is_in_transit]
    
    # -------------------------------------------------------------------------
    # Dashboard & Reports
    # -------------------------------------------------------------------------
    
    def get_dashboard(self) -> DashboardData:
        """Get dashboard summary data"""
        books = list(self._books.values())
        
        # Count by status
        by_status = {}
        for status in BookStatus:
            count = len([b for b in books if b.status == status])
            if count > 0:
                emoji, name = get_status_display(status)
                by_status[f"{emoji} {name}"] = count
        
        # Financial summary
        active = [b for b in books if b.is_active]
        sold = [b for b in books if b.status in {BookStatus.SOLD, BookStatus.COMPLETE}]
        
        total_invested = sum(b.total_source_cost for b in books)
        total_revenue = sum(b.revenue for b in sold)
        total_profit = sum(b.profit for b in sold)
        
        # Averages
        rois = [b.roi for b in sold if b.roi > 0]
        avg_roi = sum(rois) / len(rois) if rois else 0
        
        days_list = [b.days_to_sell for b in sold if b.days_to_sell is not None]
        avg_days = sum(days_list) / len(days_list) if days_list else 0
        
        return DashboardData(
            total_books=len(books),
            active_books=len(active),
            by_status=by_status,
            total_invested=round(total_invested, 2),
            total_revenue=round(total_revenue, 2),
            total_profit=round(total_profit, 2),
            total_sold=len(sold),
            average_roi=round(avg_roi, 1),
            average_days_to_sell=round(avg_days, 1),
            books_needing_attention=len(self.get_books_needing_attention())
        )
    
    def get_pipeline_view(self) -> Dict[str, List[Book]]:
        """Get books organized by pipeline stage"""
        stages = {
            'Purchasing': [BookStatus.ORDERED, BookStatus.SHIPPED_TO_YOU, 
                          BookStatus.IN_TRANSIT_TO_YOU, BookStatus.DELIVERED_TO_YOU],
            'Processing': [BookStatus.RECEIVED, BookStatus.PROCESSING, BookStatus.PROCESSED],
            'FBA Shipping': [BookStatus.FBA_SHIPMENT_CREATED, BookStatus.FBA_SHIPPED,
                            BookStatus.FBA_IN_TRANSIT, BookStatus.FBA_DELIVERED,
                            BookStatus.FBA_RECEIVING],
            'Selling': [BookStatus.FBA_AVAILABLE, BookStatus.RESERVED],
            'Complete': [BookStatus.SOLD, BookStatus.COMPLETE],
            'Issues': [BookStatus.RETURNED, BookStatus.STRANDED, BookStatus.LOST, BookStatus.CANCELLED]
        }
        
        result = {}
        for stage_name, statuses in stages.items():
            books = [b for b in self._books.values() if b.status in statuses]
            if books:
                result[stage_name] = books
        
        return result
    
    def generate_pnl_report(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> dict:
        """Generate profit and loss report"""
        sold_books = [
            b for b in self._books.values()
            if b.status in {BookStatus.SOLD, BookStatus.COMPLETE}
        ]
        
        # Filter by date if provided
        if start_date:
            start = datetime.fromisoformat(start_date)
            sold_books = [b for b in sold_books if b.sale_date and b.sale_date >= start]
        if end_date:
            end = datetime.fromisoformat(end_date)
            sold_books = [b for b in sold_books if b.sale_date and b.sale_date <= end]
        
        total_revenue = sum(b.revenue for b in sold_books)
        total_cogs = sum(b.total_source_cost for b in sold_books)
        total_fees = sum(b.total_amazon_fees for b in sold_books)
        gross_profit = total_revenue - total_cogs - total_fees
        
        return {
            'period': {
                'start': start_date,
                'end': end_date
            },
            'books_sold': len(sold_books),
            'revenue': round(total_revenue, 2),
            'cost_of_goods': round(total_cogs, 2),
            'amazon_fees': round(total_fees, 2),
            'gross_profit': round(gross_profit, 2),
            'roi_percent': round((gross_profit / total_cogs * 100) if total_cogs > 0 else 0, 1),
            'average_profit_per_book': round(gross_profit / len(sold_books) if sold_books else 0, 2)
        }
    
    # -------------------------------------------------------------------------
    # Event System
    # -------------------------------------------------------------------------
    
    def on_status_change(self, handler: Callable):
        """Register a status change handler"""
        self._status_handlers.append(handler)
        return handler
    
    def _emit_status_change(self, book: Book, old_status: BookStatus, new_status: BookStatus):
        """Emit status change event to all handlers"""
        for handler in self._status_handlers:
            try:
                handler(book, old_status, new_status)
            except Exception as e:
                print(f"Error in status handler: {e}")
    
    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------
    
    def _save_book(self, book: Book):
        """Save book to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO books (id, asin, data, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                book.id,
                book.asin,
                json.dumps(book.to_dict()),
                book.status.value if book.status else None,
                book.created_at.isoformat(),
                book.updated_at.isoformat()
            ))
    
    def _load_books(self):
        """Load all books from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM books").fetchall()
            
            for row in rows:
                data = json.loads(row['data'])
                book = Book.from_dict(data)
                self._books[book.id] = book
    
    def export_to_json(self, filepath: str):
        """Export all books to JSON file"""
        data = [b.to_dict() for b in self._books.values()]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='S-Agent: Shipping & Status Agent')
    parser.add_argument('command', choices=['dashboard', 'list', 'add', 'update', 'export'])
    parser.add_argument('--status', help='Filter by status')
    parser.add_argument('--asin', help='Book ASIN')
    parser.add_argument('--id', help='Book ID')
    
    args = parser.parse_args()
    
    agent = SAgent()
    
    if args.command == 'dashboard':
        dashboard = agent.get_dashboard()
        print(f"\n{'='*50}")
        print("📊 S-AGENT DASHBOARD")
        print(f"{'='*50}\n")
        print(f"Total Books: {dashboard.total_books}")
        print(f"Active: {dashboard.active_books}")
        print(f"Sold: {dashboard.total_sold}")
        print(f"\nBy Status:")
        for status, count in dashboard.by_status.items():
            print(f"  {status}: {count}")
        print(f"\n💰 Financials:")
        print(f"  Invested: ${dashboard.total_invested:,.2f}")
        print(f"  Revenue: ${dashboard.total_revenue:,.2f}")
        print(f"  Profit: ${dashboard.total_profit:,.2f}")
        print(f"  Avg ROI: {dashboard.average_roi}%")
        print(f"  Avg Days to Sell: {dashboard.average_days_to_sell}")
        
        if dashboard.books_needing_attention > 0:
            print(f"\n⚠️ {dashboard.books_needing_attention} books need attention!")
    
    elif args.command == 'list':
        if args.status:
            status = BookStatus(args.status)
            books = agent.get_books_by_status(status)
        else:
            books = agent.get_active_books()
        
        print(f"\nFound {len(books)} books:\n")
        for book in books:
            emoji, status_name = get_status_display(book.status)
            print(f"{emoji} {book.asin} - {book.title[:40]}... [{status_name}]")
