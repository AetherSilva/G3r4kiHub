"""
Amazon Product Advertising API integration
Fetches product information, prices, and builds affiliate URLs
"""

from typing import List, Optional, Dict
from amazon_paapi import AmazonApi, GetItemsResource
import logging
from config import settings

logger = logging.getLogger(__name__)


class AmazonAPIClient:
    """Client for Amazon Product Advertising API"""

    def __init__(self):
        """Initialize Amazon API client"""
        try:
            self.amazon = AmazonApi(
                access_key=settings.amazon_access_key,
                secret_key=settings.amazon_secret_key,
                partner_tag=settings.amazon_partner_tag,
                country=settings.amazon_country
            )
            logger.info("Amazon API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Amazon API: {str(e)}")
            self.amazon = None

    def build_affiliate_url(self, product_url: str, asin: str = None) -> str:
        """
        Build affiliate URL with partner tag
        
        Args:
            product_url: Original Amazon product URL
            asin: Optional ASIN to build URL from
            
        Returns:
            Affiliate URL with partner tag
        """
        if asin:
            return f"https://www.amazon.com/dp/{asin}?tag={settings.amazon_partner_tag}"
        
        # Add tag to existing URL
        separator = "&" if "?" in product_url else "?"
        return f"{product_url}{separator}tag={settings.amazon_partner_tag}"

    def get_product_by_asin(self, asin: str) -> Optional[Dict]:
        """
        Fetch product details by ASIN
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            Product details dict or None if fetch fails
        """
        if not self.amazon:
            logger.warning("Amazon API client not initialized")
            return None

        try:
            response = self.amazon.get_items(
                item_ids=[asin],
                resources=[
                    GetItemsResource.IMAGES_PRIMARY_LARGE,
                    GetItemsResource.ITEM_INFO_TITLE,
                    GetItemsResource.OFFERS_LISTINGS_PRICE,
                    GetItemsResource.ITEM_INFO_CLASSIFICATIONS,
                ]
            )

            if not response or not response.get("Items"):
                logger.warning(f"No product found for ASIN: {asin}")
                return None

            item = response["Items"][0]
            
            # Extract product information
            product_data = {
                "asin": asin,
                "title": self._extract_title(item),
                "price": self._extract_price(item),
                "original_price": self._extract_original_price(item),
                "discount_percent": self._calculate_discount(item),
                "image_url": self._extract_image(item),
                "category": self._extract_category(item),
            }
            
            # Build affiliate URL
            product_data["affiliate_url"] = self.build_affiliate_url("", asin)
            
            logger.info(f"Successfully fetched product: {product_data['title']}")
            return product_data

        except Exception as e:
            logger.error(f"Error fetching product {asin}: {str(e)}")
            return None

    def get_products_by_asin_list(self, asins: List[str]) -> List[Dict]:
        """
        Fetch multiple products by ASIN list
        
        Args:
            asins: List of ASINs
            
        Returns:
            List of product details
        """
        products = []
        for asin in asins:
            product = self.get_product_by_asin(asin)
            if product:
                products.append(product)
        return products

    def search_deals(self, keywords: str = "deal", max_results: int = 10) -> List[Dict]:
        """
        Search for deals (currently uses mock data)
        In production, integrate with deal APIs like CamelCamelCamel, Slickdeals, etc.
        
        Args:
            keywords: Search keywords
            max_results: Maximum results to return
            
        Returns:
            List of deal products
        """
        # This is a placeholder - integrate with actual deal sources
        logger.info(f"Searching for deals with keywords: {keywords}")
        return []

    # ============ Helper Methods ============

    @staticmethod
    def _extract_title(item: Dict) -> str:
        """Extract product title from item"""
        try:
            return item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Unknown")
        except:
            return "Unknown"

    @staticmethod
    def _extract_price(item: Dict) -> float:
        """Extract current price from item"""
        try:
            offers = item.get("Offers", {}).get("Listings", [])
            if offers:
                price_str = offers[0].get("Price", {}).get("DisplayAmount", "0")
                # Remove currency symbol and convert to float
                price_str = price_str.replace("$", "").replace(",", "")
                return float(price_str)
        except:
            pass
        return 0.0

    @staticmethod
    def _extract_original_price(item: Dict) -> Optional[float]:
        """Extract original/list price from item"""
        try:
            # Some products have savings information
            offers = item.get("Offers", {}).get("Listings", [])
            if offers:
                savings = offers[0].get("SavingsAmount", {})
                if savings:
                    current = float(
                        offers[0].get("Price", {}).get("DisplayAmount", "0")
                        .replace("$", "").replace(",", "")
                    )
                    savings_amount = float(
                        savings.get("DisplayAmount", "0")
                        .replace("$", "").replace(",", "")
                    )
                    return current + savings_amount
        except:
            pass
        return None

    @staticmethod
    def _calculate_discount(item: Dict) -> Optional[float]:
        """Calculate discount percentage"""
        try:
            offers = item.get("Offers", {}).get("Listings", [])
            if offers:
                discount_data = offers[0].get("PricePerUnit", {})
                if discount_data:
                    return discount_data.get("PercentageSaved", 0)
        except:
            pass
        return None

    @staticmethod
    def _extract_image(item: Dict) -> Optional[str]:
        """Extract product image URL"""
        try:
            return item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", None)
        except:
            return None

    @staticmethod
    def _extract_category(item: Dict) -> Optional[str]:
        """Extract product category"""
        try:
            classifications = item.get("ItemInfo", {}).get("Classifications", {})
            return classifications.get("ProductGroup", {}).get("DisplayValue", "General")
        except:
            return "General"


# Global client instance
_amazon_client: Optional[AmazonAPIClient] = None


def get_amazon_client() -> AmazonAPIClient:
    """Get or create Amazon API client"""
    global _amazon_client
    if _amazon_client is None:
        _amazon_client = AmazonAPIClient()
    return _amazon_client
