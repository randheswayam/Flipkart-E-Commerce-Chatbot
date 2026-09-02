from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder
import re

encoder = HuggingFaceEncoder(
    name="sentence-transformers/all-MiniLM-L6-v2"
)

faq = Route(
    name='faq',
    utterances=[
        "What is the return policy of the products?",
        "Do I get discount with the HDFC credit card?",
        "How can I track my order?",
        "What payment methods are accepted?",
        "How long does it take to process a refund?",
    ]
)

sql = Route(
    name='sql',
    utterances=[
        "I want to buy nike shoes that have 50% discount.",
        "Are there any shoes under Rs. 3000?",
        "Do you have formal shoes in size 9?",
        "Are there any Puma shoes on sale?",
        "What is the price of puma running shoes?",
    ]
)

router = RouteLayer(routes=[faq, sql], encoder=encoder)


def normalize_query(query):
    normalized_query = re.sub(r"\s+", " ", query).strip()
    normalized_query = re.sub(r"(?i)(\d+(?:\.\d+)?)\s*k\b", r"\1 thousand", normalized_query)
    normalized_query = re.sub(r"(?i)\brs\.?\s*", "Rs. ", normalized_query)
    return normalized_query


def classify_query(query):
    normalized_query = normalize_query(query)
    lowered_query = normalized_query.casefold()

    faq_terms = (
        "return", "refund", "track", "payment", "pay", "paid", "cash", "cash on delivery", "cod",
        "cancel", "modify order", "delivery", "discount", "hdfc", "promotion",
        "offer", "exchange", "defective", "customer care", "support",
    )
    product_terms = (
        "buy", "find", "show", "recommend", "product", "shoe", "shoes", "price",
        "under", "below", "less than", "discount", "rating", "brand", "size",
        "available", "sale", "top", "best", "cheapest", "expensive",
    )

    if any(term in lowered_query for term in faq_terms) and not any(
        term in lowered_query for term in ("shoe", "shoes", "product", "price", "brand")
    ):
        return "faq", normalized_query
    if any(term in lowered_query for term in product_terms):
        return "sql", normalized_query

    route = router(normalized_query)
    return route.name if route else "unknown", normalized_query

if __name__ == "__main__":
    print(router("What is your policy on defective product?").name)
    print(router("Pink Puma shoes in price range 5000 to 1000").name)