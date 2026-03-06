import pandas as pd


REQUIRED_COLUMNS = {
    "organization_name",
    "domain",
    "cta_phrase",
    "service_name",
    "offer_title",
    "offer_description",
    "location",
    "phone"
}


def load_campaigns(path: str):
    """
    Loads campaign data from Excel and returns a list of
    clean, runtime-safe campaign dicts.
    """

    df = pd.read_excel(path)

    # 🔴 Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Campaign file missing required columns: {', '.join(missing)}"
        )

    campaigns = []

    for _, row in df.iterrows():
        # Skip empty rows
        if pd.isna(row["domain"]) or pd.isna(row["phone"]):
            continue

        campaign = {
            "organization_name": str(row["organization_name"]).strip().lower(),
            "domain": str(row["domain"]).strip().lower(),
            "cta_phrase": str(row["cta_phrase"]).strip().lower(),
            "service_name": str(row["service_name"]).strip(),
            "offer_title": str(row["offer_title"]).strip(),
            "offer_description": str(row["offer_description"]).strip(),
            "location": str(row["location"]).strip(),
            "phone": str(row["phone"]).strip(),
        }

        # 🔒 Hard domain validation
        if campaign["domain"] not in {"healthcare", "finance", "real_estate"}:
            print(
                f"[Campaign Skipped] Invalid domain: {campaign['domain']}"
            )
            continue

        campaigns.append(campaign)

    if not campaigns:
        raise ValueError("No valid campaigns found in Excel file.")

    return campaigns