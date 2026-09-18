NAVIGATION = [
    ("dashboard", "Overview", "/"),
    ("global-risk", "Global risk", "/global-risk/"),
    ("supply-chain", "Supply chain", "/supply-chain/"),
    ("suppliers", "Suppliers", "/suppliers/"),
    ("factories", "Factories", "/factories/"),
    ("vehicle-safety", "Vehicle safety", "/vehicle-safety/"),
    ("recalls", "Recalls", "/recalls/"),
    ("complaints", "Complaints", "/complaints/"),
    ("analytics", "Analytics", "/analytics/"),
    ("data-health", "Data health", "/data-health/"),
]


def navigation(request):
    mode = "live" if request.GET.get("mode") == "live" else "demo"
    return {"navigation": NAVIGATION, "mode": mode}
