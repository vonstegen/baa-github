"""
Keepa API Client

Fetches historical data from Keepa API for book analysis.

API Documentation: https://keepa.com/#!discuss/t/pa-api

Required data:
- BSR history (90 days)
- Price history (Amazon, FBA, FBM)
- Offer counts
- Sales rank drops (for velocity estimation)
"""

import os
import time
import requests
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime, timedelta


@dataclass
class KeepaProduct:
    """Product data from Keepa"""
    asin: str
    title: str
    
    # Current values
    current_bsr: Optional[int] = None
    current_amazon_price: Optional[float] = None
    current_fba_price: Optional[float] = None
    current_fbm_price: Optional[float] = None
    
    # Historical averages (90 day)
    avg_bsr_90: Optional[int] = None
    avg_price_90: Optional[float] = None
    
    # Counts
    fba_offer_count: Optional[int] = None
    fbm_offer_count: Optional[int] = None
    
    # Sales estimation
    bsr_drops_30: Optional[int] = None  # BSR drops in last 30 days
    estimated_monthly_sales: Optional[float] = None
    
    # Trends
    price_trend: Optional[str] = None  # rising, stable, declining
    bsr_trend: Optional[str] = None
    
    # Metadata
    last_updated: datetime = None


class KeepaClient:
    """
    Keepa API client
    
    Rate limits:
    - Free tier: ~10 requests/minute
    - Paid tier: Higher limits based on plan
    """
    
    BASE_URL = "https://api.keepa.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('KEEPA_API_KEY')
        if not self.api_key:
            raise ValueError("Keepa API key required. Set KEEPA_API_KEY env var.")
        
        self.tokens_left = None
        self.last_request = None
        self.min_delay = 0.5  # Minimum seconds between requests
    
    def _wait_for_rate_limit(self):
        """Respect rate limits"""
        if self.last_request:
            elapsed = time.time() - self.last_request
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
        self.last_request = time.time()
    
    def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make API request"""
        self._wait_for_rate_limit()
        
        params['key'] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        self.tokens_left = data.get('tokensLeft')
        
        return data
    
    def get_product(self, asin: str, domain: int = 1) -> Optional[KeepaProduct]:
        """
        Fetch product data from Keepa
        
        Args:
            asin: Amazon ASIN
            domain: Amazon domain (1=US, 2=UK, 3=DE, etc.)
        
        Returns:
            KeepaProduct or None if not found
        """
        try:
            data = self._make_request('product', {
                'domain': domain,
                'asin': asin,
                'stats': 90,  # Include 90-day stats
                'offers': 20   # Include offer data
            })
            
            if not data.get('products'):
                return None
            
            product_data = data['products'][0]
            return self._parse_product(product_data)
            
        except requests.RequestException as e:
            print(f"Keepa API error for {asin}: {e}")
            return None
    
    def get_products_batch(
        self, 
        asins: List[str], 
        domain: int = 1
    ) -> Dict[str, KeepaProduct]:
        """
        Fetch multiple products (up to 100)
        
        More efficient than individual requests.
        """
        results = {}
        
        # Keepa allows up to 100 ASINs per request
        batch_size = 100
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            
            try:
                data = self._make_request('product', {
                    'domain': domain,
                    'asin': ','.join(batch),
                    'stats': 90,
                    'offers': 20
                })
                
                for product_data in data.get('products', []):
                    if product_data:
                        product = self._parse_product(product_data)
                        if product:
                            results[product.asin] = product
                            
            except requests.RequestException as e:
                print(f"Keepa batch error: {e}")
        
        return results
    
    def _parse_product(self, data: dict) -> Optional[KeepaProduct]:
        """Parse Keepa API response into KeepaProduct"""
        try:
            asin = data.get('asin')
            if not asin:
                return None
            
            # Parse stats
            stats = data.get('stats', {})
            
            # Current values (index -1 or latest)
            current = stats.get('current', [])
            
            # 90-day averages
            avg_90 = stats.get('avg90', [])
            
            # Parse BSR
            current_bsr = self._get_stat(current, 3)  # Index 3 = sales rank
            avg_bsr = self._get_stat(avg_90, 3)
            
            # Parse prices (Keepa stores in cents)
            amazon_price = self._parse_price(self._get_stat(current, 0))
            fba_price = self._parse_price(self._get_stat(current, 10))
            fbm_price = self._parse_price(self._get_stat(current, 7))
            avg_price = self._parse_price(self._get_stat(avg_90, 0))
            
            # Offer counts
            offer_counts = data.get('offers', {})
            
            # Estimate sales from BSR drops
            bsr_drops = self._count_bsr_drops(data.get('csv', []), days=30)
            monthly_sales = self._estimate_sales(bsr_drops, current_bsr)
            
            # Determine trends
            price_trend = self._calculate_trend(data.get('csv', []), 0)
            bsr_trend = self._calculate_trend(data.get('csv', []), 3)
            
            return KeepaProduct(
                asin=asin,
                title=data.get('title', ''),
                current_bsr=current_bsr,
                current_amazon_price=amazon_price,
                current_fba_price=fba_price,
                current_fbm_price=fbm_price,
                avg_bsr_90=avg_bsr,
                avg_price_90=avg_price,
                fba_offer_count=len([o for o in data.get('offers', []) if o.get('isFBA')]),
                fbm_offer_count=len([o for o in data.get('offers', []) if not o.get('isFBA')]),
                bsr_drops_30=bsr_drops,
                estimated_monthly_sales=monthly_sales,
                price_trend=price_trend,
                bsr_trend=bsr_trend,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            print(f"Error parsing Keepa data: {e}")
            return None
    
    def _get_stat(self, stats: list, index: int) -> Optional[int]:
        """Safely get stat value"""
        try:
            if stats and len(stats) > index:
                val = stats[index]
                if val and val > 0:
                    return val
        except (IndexError, TypeError):
            pass
        return None
    
    def _parse_price(self, value: Optional[int]) -> Optional[float]:
        """Convert Keepa price (cents) to dollars"""
        if value and value > 0:
            return value / 100.0
        return None
    
    def _count_bsr_drops(self, csv_data: list, days: int = 30) -> int:
        """
        Count BSR drops in the last N days.
        
        Each significant BSR drop indicates a sale.
        
        Note: Properly parsing Keepa CSV data requires understanding their format.
        For now, we estimate from current BSR using industry formulas.
        """
        # TODO: Implement actual BSR drop counting from CSV data
        # For now, return -1 to signal "use BSR estimation instead"
        return -1
    
    def _estimate_sales_from_bsr(self, bsr: int) -> float:
        """
        Estimate monthly sales from BSR using industry formulas.
        
        This is an approximation based on Amazon Books category data.
        Formula derived from various seller tools and research.
        
        BSR Range -> Estimated Monthly Sales:
        1-1,000: 500+ sales/month
        1,000-10,000: 50-500 sales/month  
        10,000-50,000: 10-50 sales/month
        50,000-100,000: 5-10 sales/month
        100,000-500,000: 1-5 sales/month
        500,000-1,000,000: 0.5-1 sales/month
        1,000,000+: <0.5 sales/month
        """
        if bsr is None or bsr <= 0:
            return None
        
        # Logarithmic estimation formula for books category
        # Based on: sales ≈ (100000 / BSR) ^ 0.8
        import math
        
        if bsr <= 1000:
            return 300 + (1000 - bsr) * 0.5  # 300-800 sales
        elif bsr <= 10000:
            return 30 + (10000 - bsr) / 300  # 30-60 sales
        elif bsr <= 50000:
            return 10 + (50000 - bsr) / 4000  # 10-20 sales
        elif bsr <= 100000:
            return 5 + (100000 - bsr) / 10000  # 5-10 sales
        elif bsr <= 200000:
            return 3 + (200000 - bsr) / 50000  # 3-5 sales
        elif bsr <= 500000:
            return 1 + (500000 - bsr) / 150000  # 1-3 sales
        elif bsr <= 1000000:
            return 0.5 + (1000000 - bsr) / 1000000  # 0.5-1 sales
        else:
            return 0.3  # Very slow seller
    
    def _estimate_sales(self, bsr_drops: int, current_bsr: int = None) -> float:
        """
        Estimate monthly sales from BSR drops or current BSR.
        
        If BSR drops are available (>= 0), use those.
        Otherwise, estimate from current BSR.
        """
        if bsr_drops >= 0:
            # Each BSR drop roughly = 1 sale
            return float(bsr_drops)
        elif current_bsr:
            # Fallback to BSR-based estimation
            return self._estimate_sales_from_bsr(current_bsr)
        else:
            return None
    
    def _calculate_trend(self, csv_data: list, index: int) -> str:
        """
        Calculate price/BSR trend from historical data.
        
        Returns: 'rising', 'stable', or 'declining'
        """
        # TODO: Implement trend calculation
        return 'stable'
    
    def get_tokens_remaining(self) -> Optional[int]:
        """Get remaining API tokens"""
        return self.tokens_left


# Example usage
if __name__ == "__main__":
    # Requires KEEPA_API_KEY environment variable
    try:
        client = KeepaClient()
        
        # Test single product
        product = client.get_product("1234567890")
        if product:
            print(f"Title: {product.title}")
            print(f"BSR: {product.current_bsr}")
            print(f"FBA Price: ${product.current_fba_price}")
            print(f"Est. Monthly Sales: {product.estimated_monthly_sales}")
        
        print(f"Tokens remaining: {client.get_tokens_remaining()}")
        
    except ValueError as e:
        print(f"Setup error: {e}")
        print("Set KEEPA_API_KEY environment variable to use Keepa integration")
