"""
F-Agent Decision Engine

Makes BUY/SKIP/WATCH decisions based on multiple criteria:
- Eligibility status (from SC Extension)
- Sales metrics (from Keepa)
- ROI calculation
- Competition analysis
- Publisher watchlist
"""

import yaml
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime
from pathlib import Path


class Decision(Enum):
    BUY = "BUY"
    SKIP = "SKIP"
    WATCH = "WATCH"


class SkipReason(Enum):
    RESTRICTED = "Product is restricted"
    LOW_ROI = "ROI below threshold"
    HIGH_BSR = "BSR too high"
    LOW_SALES = "Insufficient sales velocity"
    TOO_MUCH_COMPETITION = "Too many FBA sellers"
    PUBLISHER_WATCHLIST = "Publisher on watchlist"
    PRICE_DECLINING = "Price trend declining"
    APPROVAL_UNLIKELY = "Approval success rate too low"
    UNKNOWN_ELIGIBILITY = "Could not determine eligibility"


@dataclass
class ProductData:
    """All data needed for decision"""
    asin: str
    
    # From SC Extension
    eligibility_status: str  # GOOD, NEED_APPROVAL, RESTRICTED
    
    # From Keepa
    bsr: Optional[int] = None
    bsr_90_day_avg: Optional[int] = None
    monthly_sales_estimate: Optional[float] = None
    current_price: Optional[float] = None
    price_90_day_avg: Optional[float] = None
    price_trend: Optional[str] = None  # rising, stable, declining
    fba_seller_count: Optional[int] = None
    
    # From source
    source_price: Optional[float] = None
    source_name: Optional[str] = None
    
    # Book details
    title: Optional[str] = None
    publisher: Optional[str] = None
    
    
@dataclass
class DecisionResult:
    """Result of decision engine"""
    asin: str
    decision: Decision
    reason: Optional[str] = None
    skip_reasons: Optional[List[SkipReason]] = None
    
    # Calculated values
    estimated_roi: Optional[float] = None
    estimated_profit: Optional[float] = None
    confidence: Optional[float] = None  # 0-1
    
    # Recommendations
    max_buy_price: Optional[float] = None
    recommended_sell_price: Optional[float] = None
    
    # Metadata
    decided_at: datetime = None
    
    def __post_init__(self):
        if self.decided_at is None:
            self.decided_at = datetime.now()


class FeeCalculator:
    """Calculate Amazon FBA fees (2025 rates)"""
    
    # 2025 FBA fee structure for books
    REFERRAL_FEE_PERCENT = 0.15  # 15%
    MINIMUM_REFERRAL_FEE = 0.30  # $0.30
    
    # FBA fulfillment fees by size (books are typically standard)
    FBA_FEES = {
        'small_standard': 3.22,   # Up to 16oz
        'large_standard': 4.95,   # 1-2 lb
        'large_standard_2': 5.95, # 2-3 lb
    }
    
    INBOUND_PLACEMENT_FEE = 0.27  # Per unit average
    
    @classmethod
    def calculate_fees(
        cls, 
        sell_price: float, 
        weight_oz: float = 12
    ) -> dict:
        """Calculate all fees for a book sale"""
        
        # Referral fee (15% or $0.30 minimum)
        referral_fee = max(
            sell_price * cls.REFERRAL_FEE_PERCENT,
            cls.MINIMUM_REFERRAL_FEE
        )
        
        # FBA fee based on weight
        if weight_oz <= 16:
            fba_fee = cls.FBA_FEES['small_standard']
        elif weight_oz <= 32:
            fba_fee = cls.FBA_FEES['large_standard']
        else:
            fba_fee = cls.FBA_FEES['large_standard_2']
        
        # Inbound placement fee
        inbound_fee = cls.INBOUND_PLACEMENT_FEE
        
        total_fees = referral_fee + fba_fee + inbound_fee
        
        return {
            'referral_fee': round(referral_fee, 2),
            'fba_fee': round(fba_fee, 2),
            'inbound_fee': round(inbound_fee, 2),
            'total_fees': round(total_fees, 2)
        }
    
    @classmethod
    def calculate_profit(
        cls,
        sell_price: float,
        buy_price: float,
        weight_oz: float = 12
    ) -> dict:
        """Calculate profit and ROI"""
        fees = cls.calculate_fees(sell_price, weight_oz)
        
        gross_profit = sell_price - fees['total_fees'] - buy_price
        roi = (gross_profit / buy_price * 100) if buy_price > 0 else 0
        
        return {
            'sell_price': sell_price,
            'buy_price': buy_price,
            'fees': fees,
            'gross_profit': round(gross_profit, 2),
            'roi_percent': round(roi, 1)
        }


class DecisionEngine:
    """Main decision engine for F-Agent"""
    
    def __init__(self, config_path: str = "config/thresholds.yaml"):
        self.config = self._load_config(config_path)
        self.fee_calculator = FeeCalculator()
        self.publisher_watchlist = self._load_publisher_watchlist()
    
    def _load_config(self, config_path: str) -> dict:
        """Load decision thresholds from config"""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        
        # Default config
        return {
            'eligibility': {
                'allowed_statuses': ['GOOD'],
                'allow_need_approval': False,
                'approval_success_threshold': 0.7
            },
            'bsr': {
                'max_rank': 2000000,
                'preferred_max': 500000
            },
            'sales': {
                'min_monthly_sales': 1,
                'preferred_monthly_sales': 3
            },
            'roi': {
                'minimum_percent': 30,
                'preferred_percent': 50
            },
            'competition': {
                'max_fba_sellers': 10,
                'preferred_fba_sellers': 5
            },
            'price': {
                'min_selling_price': 10.00,
                'allow_declining_trend': False
            }
        }
    
    def _load_publisher_watchlist(self) -> set:
        """Load publisher watchlist"""
        # Publishers known to have issues (IP claims, etc.)
        return {
            'test prep company',
            'workbook publisher',
            # Add more as needed
        }
    
    def analyze(self, product: ProductData) -> DecisionResult:
        """
        Analyze product and make decision.
        
        Returns BUY, SKIP, or WATCH with reasoning.
        """
        skip_reasons = []
        confidence = 1.0
        
        # 1. Check eligibility (REQUIRED)
        eligibility_ok, eligibility_reason = self._check_eligibility(product)
        if not eligibility_ok:
            skip_reasons.append(eligibility_reason)
        
        # 2. Check BSR (REQUIRED)
        bsr_ok, bsr_reason = self._check_bsr(product)
        if not bsr_ok:
            skip_reasons.append(bsr_reason)
        
        # 3. Check sales velocity
        sales_ok, sales_reason = self._check_sales(product)
        if not sales_ok:
            skip_reasons.append(sales_reason)
            confidence *= 0.8
        
        # 4. Check competition
        comp_ok, comp_reason = self._check_competition(product)
        if not comp_ok:
            skip_reasons.append(comp_reason)
            confidence *= 0.9
        
        # 5. Check price trend
        price_ok, price_reason = self._check_price_trend(product)
        if not price_ok:
            skip_reasons.append(price_reason)
            confidence *= 0.85
        
        # 6. Check publisher
        pub_ok, pub_reason = self._check_publisher(product)
        if not pub_ok:
            skip_reasons.append(pub_reason)
        
        # 7. Calculate ROI (REQUIRED)
        roi_result = self._calculate_roi(product)
        if roi_result['skip_reason']:
            skip_reasons.append(roi_result['skip_reason'])
        
        # Make decision
        if skip_reasons:
            # Check if it's a hard skip or could be a watch
            hard_skips = {
                SkipReason.RESTRICTED,
                SkipReason.UNKNOWN_ELIGIBILITY,
                SkipReason.PUBLISHER_WATCHLIST
            }
            
            if any(r in hard_skips for r in skip_reasons):
                decision = Decision.SKIP
            elif len(skip_reasons) == 1 and skip_reasons[0] in [
                SkipReason.LOW_SALES,
                SkipReason.PRICE_DECLINING
            ]:
                decision = Decision.WATCH
            else:
                decision = Decision.SKIP
        else:
            decision = Decision.BUY
        
        return DecisionResult(
            asin=product.asin,
            decision=decision,
            reason=self._format_reason(decision, skip_reasons),
            skip_reasons=skip_reasons if skip_reasons else None,
            estimated_roi=roi_result.get('roi'),
            estimated_profit=roi_result.get('profit'),
            confidence=confidence,
            max_buy_price=roi_result.get('max_buy_price'),
            recommended_sell_price=product.current_price
        )
    
    def _check_eligibility(self, product: ProductData) -> tuple:
        """Check eligibility status"""
        status = product.eligibility_status
        
        if status == 'RESTRICTED':
            return False, SkipReason.RESTRICTED
        
        if status == 'UNKNOWN' or status == 'NOT_CHECKED':
            return False, SkipReason.UNKNOWN_ELIGIBILITY
        
        if status == 'NEED_APPROVAL':
            if not self.config['eligibility'].get('allow_need_approval', False):
                return False, SkipReason.APPROVAL_UNLIKELY
        
        return True, None
    
    def _check_bsr(self, product: ProductData) -> tuple:
        """Check BSR threshold"""
        if product.bsr is None:
            return True, None  # Can't check, pass
        
        max_bsr = self.config['bsr']['max_rank']
        if product.bsr > max_bsr:
            return False, SkipReason.HIGH_BSR
        
        return True, None
    
    def _check_sales(self, product: ProductData) -> tuple:
        """Check sales velocity"""
        if product.monthly_sales_estimate is None:
            return True, None  # Can't check, pass
        
        min_sales = self.config['sales']['min_monthly_sales']
        if product.monthly_sales_estimate < min_sales:
            return False, SkipReason.LOW_SALES
        
        return True, None
    
    def _check_competition(self, product: ProductData) -> tuple:
        """Check FBA competition"""
        if product.fba_seller_count is None:
            return True, None
        
        max_sellers = self.config['competition']['max_fba_sellers']
        if product.fba_seller_count > max_sellers:
            return False, SkipReason.TOO_MUCH_COMPETITION
        
        return True, None
    
    def _check_price_trend(self, product: ProductData) -> tuple:
        """Check price trend"""
        if product.price_trend is None:
            return True, None
        
        if product.price_trend == 'declining':
            if not self.config['price'].get('allow_declining_trend', False):
                return False, SkipReason.PRICE_DECLINING
        
        return True, None
    
    def _check_publisher(self, product: ProductData) -> tuple:
        """Check publisher watchlist"""
        if product.publisher is None:
            return True, None
        
        if product.publisher.lower() in self.publisher_watchlist:
            return False, SkipReason.PUBLISHER_WATCHLIST
        
        return True, None
    
    def _calculate_roi(self, product: ProductData) -> dict:
        """Calculate ROI and determine if profitable"""
        result = {
            'roi': None,
            'profit': None,
            'max_buy_price': None,
            'skip_reason': None
        }
        
        if product.current_price is None or product.source_price is None:
            return result
        
        # Calculate with current prices
        profit_calc = self.fee_calculator.calculate_profit(
            sell_price=product.current_price,
            buy_price=product.source_price
        )
        
        result['roi'] = profit_calc['roi_percent']
        result['profit'] = profit_calc['gross_profit']
        
        # Check minimum ROI
        min_roi = self.config['roi']['minimum_percent']
        if profit_calc['roi_percent'] < min_roi:
            result['skip_reason'] = SkipReason.LOW_ROI
        
        # Calculate max buy price for target ROI
        target_roi = self.config['roi']['preferred_percent'] / 100
        fees = self.fee_calculator.calculate_fees(product.current_price)
        max_buy = (product.current_price - fees['total_fees']) / (1 + target_roi)
        result['max_buy_price'] = round(max_buy, 2)
        
        return result
    
    def _format_reason(
        self, 
        decision: Decision, 
        skip_reasons: List[SkipReason]
    ) -> str:
        """Format decision reason for output"""
        if decision == Decision.BUY:
            return "All criteria passed - recommend purchase"
        elif decision == Decision.WATCH:
            reasons = [r.value for r in skip_reasons]
            return f"Monitor for improvement: {', '.join(reasons)}"
        else:
            reasons = [r.value for r in skip_reasons]
            return f"Skip: {', '.join(reasons)}"


# Example usage
if __name__ == "__main__":
    engine = DecisionEngine()
    
    # Test product
    product = ProductData(
        asin="1234567890",
        eligibility_status="GOOD",
        bsr=150000,
        monthly_sales_estimate=5,
        current_price=24.99,
        source_price=10.99,
        fba_seller_count=3,
        price_trend="stable",
        title="Test Book",
        publisher="Good Publisher"
    )
    
    result = engine.analyze(product)
    
    print(f"ASIN: {result.asin}")
    print(f"Decision: {result.decision.value}")
    print(f"Reason: {result.reason}")
    print(f"Estimated ROI: {result.estimated_roi}%")
    print(f"Estimated Profit: ${result.estimated_profit}")
    print(f"Max Buy Price: ${result.max_buy_price}")
    print(f"Confidence: {result.confidence}")
