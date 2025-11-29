"""
S-Agent Book Model

The core data model for tracking books through the arbitrage pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import uuid

from .status import BookStatus, StatusHistory, StatusEvent


@dataclass
class Book:
    """
    Complete book record tracking the entire lifecycle.
    """
    
    # Identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asin: str = ""
    isbn: str = ""
    title: str = ""
    
    # Source purchase details
    source_marketplace: str = ""      # eBay, AbeBooks, ThriftBooks, etc.
    source_order_id: str = ""
    source_url: str = ""
    source_seller: str = ""
    source_price: float = 0.0
    source_shipping: float = 0.0
    source_tax: float = 0.0
    source_tracking: str = ""
    source_carrier: str = ""
    ordered_at: datetime = None
    
    # Book condition
    expected_condition: str = ""      # Condition listed by source
    actual_condition: str = ""        # Condition after inspection
    condition_notes: str = ""
    
    # FBA details
    fba_shipment_id: str = ""
    fba_tracking: str = ""
    fba_carrier: str = ""
    fnsku: str = ""
    msku: str = ""                    # Merchant SKU
    
    # Listing details
    listing_price: float = 0.0
    listing_condition: str = ""       # Amazon condition (New, Used - Like New, etc.)
    listing_notes: str = ""           # Condition notes for listing
    listed_at: datetime = None
    
    # Sale details
    sale_order_id: str = ""
    sale_price: float = 0.0
    sale_date: datetime = None
    buyer_paid_shipping: float = 0.0
    
    # Amazon fees (populated after sale)
    referral_fee: float = 0.0
    fba_fee: float = 0.0
    other_fees: float = 0.0
    
    # Status tracking
    _status_history: StatusHistory = field(default_factory=StatusHistory)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # -------------------------------------------------------------------------
    # Status Properties
    # -------------------------------------------------------------------------
    
    @property
    def status(self) -> BookStatus:
        """Current status"""
        return self._status_history.current_status
    
    @property
    def status_history(self) -> List[StatusEvent]:
        """Full status history"""
        return self._status_history.events
    
    def update_status(
        self,
        new_status: BookStatus,
        source: str = "manual",
        notes: str = "",
        metadata: dict = None
    ):
        """Update book status with validation"""
        self._status_history.add_event(
            status=new_status,
            source=source,
            notes=notes,
            metadata=metadata
        )
        self.updated_at = datetime.now()
    
    # -------------------------------------------------------------------------
    # Financial Properties
    # -------------------------------------------------------------------------
    
    @property
    def total_source_cost(self) -> float:
        """Total cost from source (price + shipping + tax)"""
        return self.source_price + self.source_shipping + self.source_tax
    
    @property
    def total_amazon_fees(self) -> float:
        """Total Amazon fees"""
        return self.referral_fee + self.fba_fee + self.other_fees
    
    @property
    def total_cost(self) -> float:
        """Total cost (source + Amazon fees)"""
        return self.total_source_cost + self.total_amazon_fees
    
    @property
    def revenue(self) -> float:
        """Total revenue from sale"""
        return self.sale_price + self.buyer_paid_shipping
    
    @property
    def profit(self) -> float:
        """Net profit (revenue - total cost)"""
        if self.status not in {BookStatus.SOLD, BookStatus.COMPLETE}:
            return 0.0
        return self.revenue - self.total_cost
    
    @property
    def roi(self) -> float:
        """Return on investment percentage"""
        if self.total_source_cost <= 0:
            return 0.0
        return (self.profit / self.total_source_cost) * 100
    
    @property
    def expected_profit(self) -> float:
        """Expected profit based on listing price (before sale)"""
        if self.listing_price <= 0:
            return 0.0
        # Estimate fees
        est_referral = self.listing_price * 0.15
        est_fba = 4.50  # Average FBA fee for books
        est_total_fees = est_referral + est_fba
        return self.listing_price - self.total_source_cost - est_total_fees
    
    @property
    def expected_roi(self) -> float:
        """Expected ROI based on listing price"""
        if self.total_source_cost <= 0:
            return 0.0
        return (self.expected_profit / self.total_source_cost) * 100
    
    # -------------------------------------------------------------------------
    # Time Properties
    # -------------------------------------------------------------------------
    
    @property
    def days_since_ordered(self) -> int:
        """Days since order was placed"""
        if not self.ordered_at:
            return 0
        return (datetime.now() - self.ordered_at).days
    
    @property
    def days_since_listed(self) -> int:
        """Days since listed on Amazon"""
        if not self.listed_at:
            return 0
        return (datetime.now() - self.listed_at).days
    
    @property
    def days_to_sell(self) -> Optional[int]:
        """Days from FBA available to sold"""
        if self.status not in {BookStatus.SOLD, BookStatus.COMPLETE}:
            return None
        
        # Find when it became available
        available_time = None
        sale_time = None
        
        for event in self._status_history.events:
            if event.status == BookStatus.FBA_AVAILABLE and not available_time:
                available_time = event.timestamp
            if event.status == BookStatus.SOLD:
                sale_time = event.timestamp
        
        if available_time and sale_time:
            return (sale_time - available_time).days
        return None
    
    @property
    def total_days_in_pipeline(self) -> int:
        """Total days from ordered to current/completion"""
        return int(self._status_history.get_total_time() / 24)
    
    # -------------------------------------------------------------------------
    # State Checks
    # -------------------------------------------------------------------------
    
    @property
    def is_active(self) -> bool:
        """Is book still in active pipeline?"""
        return self.status.is_active() if self.status else True
    
    @property
    def is_sellable(self) -> bool:
        """Is book currently available for sale?"""
        return self.status.is_sellable() if self.status else False
    
    @property
    def is_in_transit(self) -> bool:
        """Is book currently in transit?"""
        return self.status.is_in_transit() if self.status else False
    
    @property
    def needs_attention(self) -> bool:
        """Does book need attention?"""
        if self.status == BookStatus.STRANDED:
            return True
        if self.status == BookStatus.FBA_AVAILABLE and self.days_since_listed > 60:
            return True  # Aging inventory
        return False
    
    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'asin': self.asin,
            'isbn': self.isbn,
            'title': self.title,
            
            'source': {
                'marketplace': self.source_marketplace,
                'order_id': self.source_order_id,
                'price': self.source_price,
                'shipping': self.source_shipping,
                'tax': self.source_tax,
                'tracking': self.source_tracking,
                'carrier': self.source_carrier,
            },
            
            'condition': {
                'expected': self.expected_condition,
                'actual': self.actual_condition,
                'notes': self.condition_notes,
            },
            
            'fba': {
                'shipment_id': self.fba_shipment_id,
                'tracking': self.fba_tracking,
                'carrier': self.fba_carrier,
                'fnsku': self.fnsku,
                'msku': self.msku,
            },
            
            'listing': {
                'price': self.listing_price,
                'condition': self.listing_condition,
                'notes': self.listing_notes,
                'listed_at': self.listed_at.isoformat() if self.listed_at else None,
            },
            
            'sale': {
                'order_id': self.sale_order_id,
                'price': self.sale_price,
                'date': self.sale_date.isoformat() if self.sale_date else None,
            },
            
            'fees': {
                'referral': self.referral_fee,
                'fba': self.fba_fee,
                'other': self.other_fees,
                'total': self.total_amazon_fees,
            },
            
            'financials': {
                'total_cost': self.total_cost,
                'revenue': self.revenue,
                'profit': self.profit,
                'roi': self.roi,
                'expected_profit': self.expected_profit,
                'expected_roi': self.expected_roi,
            },
            
            'status': {
                'current': self.status.value if self.status else None,
                'is_active': self.is_active,
                'history': self._status_history.to_list(),
            },
            
            'timing': {
                'ordered_at': self.ordered_at.isoformat() if self.ordered_at else None,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat(),
                'days_since_ordered': self.days_since_ordered,
                'days_since_listed': self.days_since_listed,
                'days_to_sell': self.days_to_sell,
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Book':
        """Create from dictionary"""
        book = cls(
            id=data.get('id'),
            asin=data.get('asin', ''),
            isbn=data.get('isbn', ''),
            title=data.get('title', ''),
        )
        
        # Populate source
        source = data.get('source', {})
        book.source_marketplace = source.get('marketplace', '')
        book.source_order_id = source.get('order_id', '')
        book.source_price = source.get('price', 0.0)
        book.source_shipping = source.get('shipping', 0.0)
        book.source_tax = source.get('tax', 0.0)
        book.source_tracking = source.get('tracking', '')
        book.source_carrier = source.get('carrier', '')
        
        # ... continue for other fields
        
        return book
