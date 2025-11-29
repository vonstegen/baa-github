"""
S-Agent Status Model

Defines all possible book statuses and valid transitions.
"""

from enum import Enum, auto
from typing import Set, Dict, List
from dataclasses import dataclass
from datetime import datetime


class BookStatus(Enum):
    """All possible statuses for a book in the system"""
    
    # Purchase phase
    ORDERED = "ordered"
    SHIPPED_TO_YOU = "shipped_to_you"
    IN_TRANSIT_TO_YOU = "in_transit_to_you"
    DELIVERED_TO_YOU = "delivered_to_you"
    
    # Processing phase
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    
    # FBA shipping phase
    FBA_SHIPMENT_CREATED = "fba_shipment_created"
    FBA_SHIPPED = "fba_shipped"
    FBA_IN_TRANSIT = "fba_in_transit"
    FBA_DELIVERED = "fba_delivered"
    FBA_RECEIVING = "fba_receiving"
    
    # Active selling phase
    FBA_AVAILABLE = "fba_available"
    RESERVED = "reserved"
    
    # Completion statuses
    SOLD = "sold"
    COMPLETE = "complete"
    
    # Problem statuses
    RETURNED = "returned"
    STRANDED = "stranded"
    LOST = "lost"
    CANCELLED = "cancelled"
    
    def is_active(self) -> bool:
        """Is the book still in the active pipeline?"""
        terminal_statuses = {
            BookStatus.COMPLETE,
            BookStatus.RETURNED,
            BookStatus.LOST,
            BookStatus.CANCELLED
        }
        return self not in terminal_statuses
    
    def is_sellable(self) -> bool:
        """Is the book available for sale?"""
        return self in {
            BookStatus.FBA_AVAILABLE,
            BookStatus.RESERVED
        }
    
    def is_in_transit(self) -> bool:
        """Is the book currently in transit?"""
        return self in {
            BookStatus.SHIPPED_TO_YOU,
            BookStatus.IN_TRANSIT_TO_YOU,
            BookStatus.FBA_SHIPPED,
            BookStatus.FBA_IN_TRANSIT
        }


# Valid status transitions
VALID_TRANSITIONS: Dict[BookStatus, Set[BookStatus]] = {
    BookStatus.ORDERED: {
        BookStatus.SHIPPED_TO_YOU,
        BookStatus.CANCELLED,
        BookStatus.LOST
    },
    BookStatus.SHIPPED_TO_YOU: {
        BookStatus.IN_TRANSIT_TO_YOU,
        BookStatus.DELIVERED_TO_YOU,
        BookStatus.LOST
    },
    BookStatus.IN_TRANSIT_TO_YOU: {
        BookStatus.DELIVERED_TO_YOU,
        BookStatus.LOST
    },
    BookStatus.DELIVERED_TO_YOU: {
        BookStatus.RECEIVED,
        BookStatus.LOST
    },
    BookStatus.RECEIVED: {
        BookStatus.PROCESSING,
        BookStatus.PROCESSED,  # Skip processing step
        BookStatus.CANCELLED   # If book is unsellable
    },
    BookStatus.PROCESSING: {
        BookStatus.PROCESSED,
        BookStatus.CANCELLED
    },
    BookStatus.PROCESSED: {
        BookStatus.FBA_SHIPMENT_CREATED
    },
    BookStatus.FBA_SHIPMENT_CREATED: {
        BookStatus.FBA_SHIPPED
    },
    BookStatus.FBA_SHIPPED: {
        BookStatus.FBA_IN_TRANSIT,
        BookStatus.FBA_DELIVERED,
        BookStatus.LOST
    },
    BookStatus.FBA_IN_TRANSIT: {
        BookStatus.FBA_DELIVERED,
        BookStatus.LOST
    },
    BookStatus.FBA_DELIVERED: {
        BookStatus.FBA_RECEIVING,
        BookStatus.LOST
    },
    BookStatus.FBA_RECEIVING: {
        BookStatus.FBA_AVAILABLE,
        BookStatus.STRANDED,
        BookStatus.LOST
    },
    BookStatus.FBA_AVAILABLE: {
        BookStatus.RESERVED,
        BookStatus.SOLD,
        BookStatus.STRANDED
    },
    BookStatus.RESERVED: {
        BookStatus.SOLD,
        BookStatus.FBA_AVAILABLE  # Order cancelled
    },
    BookStatus.SOLD: {
        BookStatus.COMPLETE,
        BookStatus.RETURNED
    },
    BookStatus.RETURNED: {
        BookStatus.FBA_AVAILABLE,  # Back in stock
        BookStatus.COMPLETE        # Write off
    },
    BookStatus.STRANDED: {
        BookStatus.FBA_AVAILABLE,  # Fixed
        BookStatus.CANCELLED       # Write off
    },
    # Terminal statuses have no transitions
    BookStatus.COMPLETE: set(),
    BookStatus.LOST: set(),
    BookStatus.CANCELLED: set()
}


def can_transition(from_status: BookStatus, to_status: BookStatus) -> bool:
    """Check if a status transition is valid"""
    return to_status in VALID_TRANSITIONS.get(from_status, set())


def get_valid_next_statuses(current_status: BookStatus) -> Set[BookStatus]:
    """Get all valid next statuses from current status"""
    return VALID_TRANSITIONS.get(current_status, set())


@dataclass
class StatusEvent:
    """Record of a status change"""
    status: BookStatus
    timestamp: datetime
    source: str  # What triggered the change (manual, tracking, api, etc.)
    notes: str = ""
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StatusHistory:
    """Manages status history for a book"""
    
    def __init__(self):
        self.events: List[StatusEvent] = []
    
    @property
    def current_status(self) -> BookStatus:
        """Get current (latest) status"""
        if not self.events:
            return None
        return self.events[-1].status
    
    def add_event(
        self,
        status: BookStatus,
        source: str = "manual",
        notes: str = "",
        metadata: dict = None
    ) -> StatusEvent:
        """Add a new status event"""
        # Validate transition
        if self.events:
            current = self.current_status
            if not can_transition(current, status):
                raise ValueError(
                    f"Invalid transition from {current.value} to {status.value}"
                )
        
        event = StatusEvent(
            status=status,
            timestamp=datetime.now(),
            source=source,
            notes=notes,
            metadata=metadata or {}
        )
        self.events.append(event)
        return event
    
    def get_time_in_status(self, status: BookStatus) -> float:
        """Get total time (hours) spent in a status"""
        total_hours = 0.0
        
        for i, event in enumerate(self.events):
            if event.status == status:
                # Find when this status ended
                if i + 1 < len(self.events):
                    end_time = self.events[i + 1].timestamp
                else:
                    end_time = datetime.now()
                
                delta = end_time - event.timestamp
                total_hours += delta.total_seconds() / 3600
        
        return total_hours
    
    def get_total_time(self) -> float:
        """Get total time (hours) from first to last/current status"""
        if not self.events:
            return 0.0
        
        start = self.events[0].timestamp
        end = self.events[-1].timestamp if self.current_status in {
            BookStatus.COMPLETE, BookStatus.LOST, BookStatus.CANCELLED
        } else datetime.now()
        
        return (end - start).total_seconds() / 3600
    
    def to_list(self) -> List[dict]:
        """Convert history to list of dicts"""
        return [
            {
                'status': e.status.value,
                'timestamp': e.timestamp.isoformat(),
                'source': e.source,
                'notes': e.notes,
                'metadata': e.metadata
            }
            for e in self.events
        ]


# Status display helpers
STATUS_DISPLAY = {
    BookStatus.ORDERED: ("📦", "Ordered"),
    BookStatus.SHIPPED_TO_YOU: ("🚚", "Shipped to You"),
    BookStatus.IN_TRANSIT_TO_YOU: ("🚛", "In Transit"),
    BookStatus.DELIVERED_TO_YOU: ("📬", "Delivered"),
    BookStatus.RECEIVED: ("✅", "Received"),
    BookStatus.PROCESSING: ("⚙️", "Processing"),
    BookStatus.PROCESSED: ("📝", "Processed"),
    BookStatus.FBA_SHIPMENT_CREATED: ("📋", "FBA Shipment Created"),
    BookStatus.FBA_SHIPPED: ("✈️", "Shipped to FBA"),
    BookStatus.FBA_IN_TRANSIT: ("🛫", "In Transit to FBA"),
    BookStatus.FBA_DELIVERED: ("🏭", "Delivered to FBA"),
    BookStatus.FBA_RECEIVING: ("🔄", "FBA Receiving"),
    BookStatus.FBA_AVAILABLE: ("🟢", "Available"),
    BookStatus.RESERVED: ("🟡", "Reserved"),
    BookStatus.SOLD: ("💰", "Sold"),
    BookStatus.COMPLETE: ("✅", "Complete"),
    BookStatus.RETURNED: ("↩️", "Returned"),
    BookStatus.STRANDED: ("⚠️", "Stranded"),
    BookStatus.LOST: ("❌", "Lost"),
    BookStatus.CANCELLED: ("🚫", "Cancelled"),
}


def get_status_display(status: BookStatus) -> tuple:
    """Get emoji and display name for status"""
    return STATUS_DISPLAY.get(status, ("❓", status.value))
