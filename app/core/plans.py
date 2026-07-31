PLAN_DETAILS = {
    "free": {
        "display_name": "Free",
        "requests_per_hour": 100,
        "can_access_premium_analytics": False,
    },
    "premium": {
        "display_name": "Premium",
        "requests_per_hour": 5000,
        "can_access_premium_analytics": True,
    },
    "enterprise": {
        "display_name": "Enterprise",
        "requests_per_hour": None,  # unlimited
        "can_access_premium_analytics": True,
    },
}