TRUSTED_SOURCES = [
    {
        "name": "USDA FoodData Central",
        "purpose": "Branded and foundational-food nutrition data; the preferred source for food search and barcode matching.",
        "refresh": "API sync after an API key is connected",
        "status": "Not connected",
    },
    {
        "name": "Open Food Facts",
        "purpose": "Supplemental community-maintained barcode coverage; values should be labeled as user-contributed where applicable.",
        "refresh": "API sync after provider review",
        "status": "Not connected",
    },
    {
        "name": "PubMed / evidence review queue",
        "purpose": "Research discovery for staff-reviewed training and nutrition education—not automatic medical advice.",
        "refresh": "Scheduled review by qualified staff",
        "status": "Not connected",
    },
]


def source_status():
    return TRUSTED_SOURCES
