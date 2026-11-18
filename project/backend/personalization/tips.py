"""Concrete money tips for students and young professionals in India."""

TIPS = [
    # food
    {"id": "food_mess_plan", "category": "food", "title": "Switch to a mess or tiffin plan",
     "message": "A monthly mess or tiffin plan (often ₹2,500-4,000) usually costs far less than ordering in daily. Try it for one month and compare."},
    {"id": "food_delivery_cap", "category": "food", "title": "Cap food delivery to 2 orders a week",
     "message": "Delivery and platform fees add ₹40-80 per Swiggy/Zomato order. Limit orders to two a week and cook or eat at the canteen on other days."},
    {"id": "food_bulk_groceries", "category": "food", "title": "Buy staples in bulk",
     "message": "Buy rice, dal, atta and oil monthly from a wholesale store or D-Mart instead of quick-commerce apps; prices are often 15-25% lower."},
    {"id": "food_cook_batch", "category": "food", "title": "Batch-cook on Sundays",
     "message": "Cooking 3-4 meals at once with flatmates cuts per-meal cost to ₹30-50 and saves late-night ordering."},
    # transport
    {"id": "transport_metro_pass", "category": "transport", "title": "Get a metro or bus pass",
     "message": "Monthly metro smart cards or student bus passes cost much less than daily tickets or autos. Check your city's student concession."},
    {"id": "transport_share_rides", "category": "transport", "title": "Share cabs and autos",
     "message": "Split Uber/Ola/Rapido rides with friends heading the same way, or use bike taxis for short solo trips."},
    {"id": "transport_cycle_walk", "category": "transport", "title": "Walk or cycle short distances",
     "message": "For trips under 2 km, walking or a rental cycle saves ₹50-100 a trip and doubles as exercise."},
    {"id": "transport_avoid_surge", "category": "transport", "title": "Avoid surge pricing",
     "message": "Plan travel around peak hours or book in advance; surge fares can be 1.5-2x the normal price."},
    # rent
    {"id": "rent_share_room", "category": "rent", "title": "Consider a shared room or PG",
     "message": "Sharing a room or moving to a PG with meals included can cut combined rent and food costs by 20-30%."},
    {"id": "rent_negotiate", "category": "rent", "title": "Negotiate rent and deposit",
     "message": "Ask for a lower deposit or a longer lock-in in exchange for lower rent, and always get a written rent agreement."},
    {"id": "rent_split_bills", "category": "rent", "title": "Split shared bills with an app",
     "message": "Track rent, Wi-Fi and maid charges with flatmates in a bill-splitting app so nobody overpays."},
    # entertainment
    {"id": "ent_audit_subscriptions", "category": "entertainment", "title": "Audit your subscriptions",
     "message": "List Netflix, Spotify, Prime, Hotstar etc. Cancel what you didn't use last month and share family plans where allowed."},
    {"id": "ent_student_discounts", "category": "entertainment", "title": "Use student discounts",
     "message": "Spotify, YouTube Premium, Amazon Prime and many software tools offer student plans at up to 50% off with a college ID."},
    {"id": "ent_weekday_movies", "category": "entertainment", "title": "Go for weekday or morning shows",
     "message": "Weekday and morning movie shows on BookMyShow are often 30-50% cheaper than weekend evenings."},
    {"id": "ent_fun_budget", "category": "entertainment", "title": "Set a weekly fun budget",
     "message": "Keep a fixed weekly amount (say ₹500) for outings in a separate UPI wallet; when it's gone, pick free plans."},
    # utilities
    {"id": "util_recharge_annual", "category": "utilities", "title": "Pick a longer recharge plan",
     "message": "84-day or annual Jio/Airtel/Vi plans usually cost less per month than 28-day recharges."},
    {"id": "util_save_power", "category": "utilities", "title": "Cut the electricity bill",
     "message": "Run ACs at 24-26°C, switch to LED bulbs and unplug chargers; this can trim the bill by 10-20%."},
    {"id": "util_share_wifi", "category": "utilities", "title": "Share one broadband connection",
     "message": "One broadband plan shared among flatmates is cheaper than everyone buying extra mobile data."},
    # other
    {"id": "other_24h_rule", "category": "other", "title": "Use the 24-hour rule",
     "message": "Wait 24 hours before any non-essential purchase above ₹1,000. Many impulse buys don't survive the wait."},
    {"id": "other_quick_commerce", "category": "other", "title": "Watch quick-commerce impulse buys",
     "message": "Blinkit/Zepto/Instamart make small add-ons easy. Make a list first and stick to it."},
    # general / savings
    {"id": "general_track_daily", "category": "general", "title": "Log expenses daily",
     "message": "Spend one minute each night logging the day's UPI and cash spends; tracking alone usually reduces spending."},
    {"id": "general_50_30_20", "category": "general", "title": "Try the 50/30/20 rule",
     "message": "Split income or allowance as 50% needs, 30% wants and 20% savings, and adjust the ratios to what's realistic for you."},
    {"id": "savings_pay_yourself_first", "category": "savings", "title": "Pay yourself first",
     "message": "Move a fixed amount to savings the day your allowance or salary arrives, before spending anything else."},
    {"id": "savings_rd_sip", "category": "savings", "title": "Start a small RD or SIP",
     "message": "A recurring deposit or an index-fund SIP can start from ₹500 a month. Starting early matters more than the amount."},
    {"id": "savings_emergency_fund", "category": "savings", "title": "Build an emergency fund",
     "message": "Aim to keep 3 months of expenses in a savings account or liquid fund before taking on investment risk."},
    {"id": "savings_round_up", "category": "savings", "title": "Round up and save",
     "message": "Round every expense up to the nearest ₹100 and move the difference to savings each week."},
]

_BY_ID = {t["id"]: t for t in TIPS}


def get_tip(tip_id):
    """Return the tip dict for an id, or None."""
    return _BY_ID.get(tip_id)
