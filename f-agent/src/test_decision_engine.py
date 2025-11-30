"""
Test F-Agent with mock eligibility data

This bypasses the extension bridge and tests the decision engine directly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from decision.engine import DecisionEngine, ProductData, Decision


def test_with_mock_data():
    """Test decision engine with sample book data"""
    
    engine = DecisionEngine()
    
    # Test books with different scenarios
    test_books = [
        {
            "name": "Good Book - Should BUY",
            "data": ProductData(
                asin="1835080030",
                eligibility_status="GOOD",  # Can sell
                bsr=150000,                  # Good BSR
                monthly_sales_estimate=5,    # Sells well
                current_price=24.99,         # Good price
                source_price=10.99,          # Low cost
                fba_seller_count=3,          # Low competition
                price_trend="stable",
                title="Cryptography Algorithms"
            )
        },
        {
            "name": "Needs Approval - Should SKIP (default config)",
            "data": ProductData(
                asin="1593278268",
                eligibility_status="NEED_APPROVAL",
                bsr=200000,
                monthly_sales_estimate=4,
                current_price=29.99,
                source_price=12.99,
                fba_seller_count=5,
                price_trend="stable",
                title="Serious Cryptography"
            )
        },
        {
            "name": "Restricted - Should SKIP",
            "data": ProductData(
                asin="1837022011",
                eligibility_status="RESTRICTED",
                bsr=100000,
                monthly_sales_estimate=8,
                current_price=39.99,
                source_price=15.99,
                fba_seller_count=2,
                price_trend="rising",
                title="Generative AI with LangChain"
            )
        },
        {
            "name": "High BSR - Should SKIP",
            "data": ProductData(
                asin="1111111111",
                eligibility_status="GOOD",
                bsr=3000000,                  # Too high!
                monthly_sales_estimate=0.5,
                current_price=19.99,
                source_price=8.99,
                fba_seller_count=2,
                price_trend="stable",
                title="Obscure Book Nobody Wants"
            )
        },
        {
            "name": "Low ROI - Should SKIP",
            "data": ProductData(
                asin="2222222222",
                eligibility_status="GOOD",
                bsr=100000,
                monthly_sales_estimate=10,
                current_price=12.99,          # Low sell price
                source_price=10.99,           # High cost = low ROI
                fba_seller_count=2,
                price_trend="stable",
                title="Cheap Book No Margin"
            )
        },
        {
            "name": "Too Much Competition - Should SKIP",
            "data": ProductData(
                asin="3333333333",
                eligibility_status="GOOD",
                bsr=50000,
                monthly_sales_estimate=15,
                current_price=34.99,
                source_price=12.99,
                fba_seller_count=25,          # Too many sellers!
                price_trend="stable",
                title="Popular Book Everyone Sells"
            )
        },
        {
            "name": "Declining Price - Should WATCH",
            "data": ProductData(
                asin="4444444444",
                eligibility_status="GOOD",
                bsr=200000,
                monthly_sales_estimate=3,
                current_price=22.99,
                source_price=9.99,
                fba_seller_count=4,
                price_trend="declining",      # Price going down
                title="Book With Falling Price"
            )
        },
        {
            "name": "Perfect Book - Should BUY",
            "data": ProductData(
                asin="5555555555",
                eligibility_status="GOOD",
                bsr=75000,                    # Great BSR
                monthly_sales_estimate=8,     # Sells fast
                current_price=44.99,          # High price
                source_price=12.99,           # Low cost = high ROI
                fba_seller_count=2,           # Low competition
                price_trend="rising",         # Price going up!
                title="Hot New Release"
            )
        },
    ]
    
    print("=" * 70)
    print("F-AGENT DECISION ENGINE TEST")
    print("=" * 70)
    print()
    
    results = {"BUY": [], "SKIP": [], "WATCH": []}
    
    for test in test_books:
        result = engine.analyze(test["data"])
        results[result.decision.value].append(test["name"])
        
        # Status icon
        icon = {"BUY": "✅", "SKIP": "❌", "WATCH": "👀"}[result.decision.value]
        
        print(f"{icon} {test['name']}")
        print(f"   ASIN: {test['data'].asin}")
        print(f"   Decision: {result.decision.value}")
        print(f"   Reason: {result.reason}")
        if result.estimated_roi:
            print(f"   ROI: {result.estimated_roi}%")
        if result.max_buy_price:
            print(f"   Max Buy Price: ${result.max_buy_price}")
        if result.estimated_profit:
            print(f"   Est. Profit: ${result.estimated_profit}")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ BUY ({len(results['BUY'])}): {', '.join(results['BUY']) or 'None'}")
    print(f"❌ SKIP ({len(results['SKIP'])}): {', '.join(results['SKIP']) or 'None'}")
    print(f"👀 WATCH ({len(results['WATCH'])}): {', '.join(results['WATCH']) or 'None'}")
    print()
    
    total = len(test_books)
    print(f"Buy Rate: {len(results['BUY']) / total * 100:.1f}%")


if __name__ == "__main__":
    test_with_mock_data()
