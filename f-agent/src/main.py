"""
F-Agent Main Orchestrator

Coordinates all F-Agent components to analyze books and make decisions.

Usage:
    from f_agent import FAgent
    
    agent = FAgent()
    results = agent.analyze_books(asins)
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from eligibility.extension_bridge import ExtensionBridge, EligibilityStatus
from decision.engine import DecisionEngine, ProductData, Decision, DecisionResult
from keepa.api_client import KeepaClient, KeepaProduct


@dataclass
class AnalysisResult:
    """Complete analysis result for a book"""
    asin: str
    decision: Decision
    decision_reason: str
    
    # Eligibility
    eligibility_status: str
    
    # Keepa data
    bsr: Optional[int] = None
    monthly_sales: Optional[float] = None
    current_price: Optional[float] = None
    fba_sellers: Optional[int] = None
    
    # Profitability
    estimated_roi: Optional[float] = None
    estimated_profit: Optional[float] = None
    max_buy_price: Optional[float] = None
    
    # Metadata
    analyzed_at: datetime = None
    confidence: Optional[float] = None
    
    def __post_init__(self):
        if self.analyzed_at is None:
            self.analyzed_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            'asin': self.asin,
            'decision': self.decision.value,
            'decision_reason': self.decision_reason,
            'eligibility_status': self.eligibility_status,
            'bsr': self.bsr,
            'monthly_sales': self.monthly_sales,
            'current_price': self.current_price,
            'fba_sellers': self.fba_sellers,
            'estimated_roi': self.estimated_roi,
            'estimated_profit': self.estimated_profit,
            'max_buy_price': self.max_buy_price,
            'confidence': self.confidence,
            'analyzed_at': self.analyzed_at.isoformat()
        }


class FAgent:
    """
    F-Agent: Finding Agent
    
    Analyzes books to determine if they should be purchased for arbitrage.
    
    Components:
    - ExtensionBridge: Gets eligibility from SC Extension
    - KeepaClient: Gets historical data from Keepa
    - DecisionEngine: Makes BUY/SKIP/WATCH decisions
    """
    
    def __init__(
        self,
        config_path: str = "config/thresholds.yaml",
        use_keepa: bool = True,
        use_extension: bool = True
    ):
        """
        Initialize F-Agent
        
        Args:
            config_path: Path to decision thresholds config
            use_keepa: Whether to fetch Keepa data
            use_extension: Whether to check eligibility via extension
        """
        self.decision_engine = DecisionEngine(config_path)
        self.extension_bridge = ExtensionBridge() if use_extension else None
        
        # Initialize Keepa if API key is available
        self.keepa_client = None
        if use_keepa and os.getenv('KEEPA_API_KEY'):
            try:
                self.keepa_client = KeepaClient()
            except ValueError:
                print("Warning: Keepa API key not set, skipping Keepa integration")
        
        self.results_log: List[AnalysisResult] = []
    
    def analyze_book(
        self,
        asin: str,
        source_price: Optional[float] = None,
        source_name: Optional[str] = None
    ) -> AnalysisResult:
        """
        Analyze a single book
        
        Args:
            asin: Amazon ASIN
            source_price: Price from source marketplace
            source_name: Name of source (eBay, AbeBooks, etc.)
        
        Returns:
            AnalysisResult with decision and supporting data
        """
        # 1. Get eligibility status
        eligibility_status = "UNKNOWN"
        if self.extension_bridge:
            eligibility_result = self.extension_bridge.check_eligibility(asin)
            eligibility_status = eligibility_result.status.value
        
        # 2. Get Keepa data
        keepa_data = None
        if self.keepa_client:
            keepa_data = self.keepa_client.get_product(asin)
        
        # 3. Build product data for decision engine
        product = ProductData(
            asin=asin,
            eligibility_status=eligibility_status,
            bsr=keepa_data.current_bsr if keepa_data else None,
            bsr_90_day_avg=keepa_data.avg_bsr_90 if keepa_data else None,
            monthly_sales_estimate=keepa_data.estimated_monthly_sales if keepa_data else None,
            current_price=keepa_data.current_fba_price or keepa_data.current_amazon_price if keepa_data else None,
            price_90_day_avg=keepa_data.avg_price_90 if keepa_data else None,
            price_trend=keepa_data.price_trend if keepa_data else None,
            fba_seller_count=keepa_data.fba_offer_count if keepa_data else None,
            source_price=source_price,
            source_name=source_name,
            title=keepa_data.title if keepa_data else None
        )
        
        # 4. Make decision
        decision_result = self.decision_engine.analyze(product)
        
        # 5. Build analysis result
        result = AnalysisResult(
            asin=asin,
            decision=decision_result.decision,
            decision_reason=decision_result.reason,
            eligibility_status=eligibility_status,
            bsr=product.bsr,
            monthly_sales=product.monthly_sales_estimate,
            current_price=product.current_price,
            fba_sellers=product.fba_seller_count,
            estimated_roi=decision_result.estimated_roi,
            estimated_profit=decision_result.estimated_profit,
            max_buy_price=decision_result.max_buy_price,
            confidence=decision_result.confidence
        )
        
        self.results_log.append(result)
        return result
    
    def analyze_books(
        self,
        asins: List[str],
        source_prices: Optional[Dict[str, float]] = None
    ) -> List[AnalysisResult]:
        """
        Analyze multiple books
        
        Args:
            asins: List of ASINs to analyze
            source_prices: Optional dict mapping ASIN to source price
        
        Returns:
            List of AnalysisResult objects
        """
        source_prices = source_prices or {}
        results = []
        
        # Batch fetch Keepa data for efficiency
        keepa_data = {}
        if self.keepa_client:
            keepa_data = self.keepa_client.get_products_batch(asins)
        
        # Batch check eligibility
        eligibility_data = {}
        if self.extension_bridge:
            eligibility_data = self.extension_bridge.check_batch(asins)
        
        # Analyze each book
        for asin in asins:
            result = self._analyze_with_cached_data(
                asin=asin,
                source_price=source_prices.get(asin),
                keepa=keepa_data.get(asin),
                eligibility=eligibility_data.get(asin)
            )
            results.append(result)
        
        return results
    
    def _analyze_with_cached_data(
        self,
        asin: str,
        source_price: Optional[float],
        keepa: Optional[KeepaProduct],
        eligibility
    ) -> AnalysisResult:
        """Analyze with pre-fetched data"""
        
        eligibility_status = eligibility.status.value if eligibility else "UNKNOWN"
        
        product = ProductData(
            asin=asin,
            eligibility_status=eligibility_status,
            bsr=keepa.current_bsr if keepa else None,
            bsr_90_day_avg=keepa.avg_bsr_90 if keepa else None,
            monthly_sales_estimate=keepa.estimated_monthly_sales if keepa else None,
            current_price=keepa.current_fba_price or keepa.current_amazon_price if keepa else None,
            price_90_day_avg=keepa.avg_price_90 if keepa else None,
            price_trend=keepa.price_trend if keepa else None,
            fba_seller_count=keepa.fba_offer_count if keepa else None,
            source_price=source_price,
            title=keepa.title if keepa else None
        )
        
        decision_result = self.decision_engine.analyze(product)
        
        return AnalysisResult(
            asin=asin,
            decision=decision_result.decision,
            decision_reason=decision_result.reason,
            eligibility_status=eligibility_status,
            bsr=product.bsr,
            monthly_sales=product.monthly_sales_estimate,
            current_price=product.current_price,
            fba_sellers=product.fba_seller_count,
            estimated_roi=decision_result.estimated_roi,
            estimated_profit=decision_result.estimated_profit,
            max_buy_price=decision_result.max_buy_price,
            confidence=decision_result.confidence
        )
    
    def get_buy_list(self) -> List[AnalysisResult]:
        """Get all books with BUY decision"""
        return [r for r in self.results_log if r.decision == Decision.BUY]
    
    def get_watch_list(self) -> List[AnalysisResult]:
        """Get all books with WATCH decision"""
        return [r for r in self.results_log if r.decision == Decision.WATCH]
    
    def get_statistics(self) -> dict:
        """Get analysis statistics"""
        total = len(self.results_log)
        if total == 0:
            return {'total': 0}
        
        buys = len([r for r in self.results_log if r.decision == Decision.BUY])
        skips = len([r for r in self.results_log if r.decision == Decision.SKIP])
        watches = len([r for r in self.results_log if r.decision == Decision.WATCH])
        
        avg_roi = None
        buy_results = [r for r in self.results_log if r.decision == Decision.BUY and r.estimated_roi]
        if buy_results:
            avg_roi = sum(r.estimated_roi for r in buy_results) / len(buy_results)
        
        return {
            'total': total,
            'buys': buys,
            'skips': skips,
            'watches': watches,
            'buy_rate': round(buys / total * 100, 1),
            'average_roi': round(avg_roi, 1) if avg_roi else None
        }
    
    def export_results(self, filepath: str = "data/analysis_results.json"):
        """Export results to JSON file"""
        import json
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(
                [r.to_dict() for r in self.results_log],
                f,
                indent=2
            )
        
        print(f"Exported {len(self.results_log)} results to {filepath}")


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='F-Agent: Book Finding Agent')
    parser.add_argument('asins', nargs='*', help='ASINs to analyze')
    parser.add_argument('--file', '-f', help='File containing ASINs (one per line)')
    parser.add_argument('--export', '-e', help='Export results to file')
    
    args = parser.parse_args()
    
    # Collect ASINs
    asins = list(args.asins) if args.asins else []
    
    if args.file:
        with open(args.file) as f:
            asins.extend([line.strip() for line in f if line.strip()])
    
    if not asins:
        print("No ASINs provided. Use: python main.py ASIN1 ASIN2 ...")
        print("Or: python main.py -f asins.txt")
        sys.exit(1)
    
    # Run analysis
    print(f"Analyzing {len(asins)} books...")
    agent = FAgent()
    
    for asin in asins:
        result = agent.analyze_book(asin)
        
        status_icon = {
            Decision.BUY: "✅",
            Decision.SKIP: "❌",
            Decision.WATCH: "👀"
        }.get(result.decision, "?")
        
        print(f"\n{status_icon} {result.asin}: {result.decision.value}")
        print(f"   Eligibility: {result.eligibility_status}")
        print(f"   Reason: {result.decision_reason}")
        if result.estimated_roi:
            print(f"   ROI: {result.estimated_roi}%")
        if result.max_buy_price:
            print(f"   Max Buy: ${result.max_buy_price}")
    
    # Print summary
    stats = agent.get_statistics()
    print(f"\n{'='*50}")
    print(f"Summary: {stats['buys']} BUY / {stats['skips']} SKIP / {stats['watches']} WATCH")
    print(f"Buy Rate: {stats['buy_rate']}%")
    if stats['average_roi']:
        print(f"Avg ROI (buys): {stats['average_roi']}%")
    
    # Export if requested
    if args.export:
        agent.export_results(args.export)
