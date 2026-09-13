import os
import yaml

ep_dir = "ingestion/data/raw_repo/episodes"
episodes = []

for ep in sorted(os.listdir(ep_dir)):
    tpath = os.path.join(ep_dir, ep, "transcript.md")
    if not os.path.exists(tpath):
        continue
    with open(tpath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1])
                meta["folder"] = ep
                episodes.append(meta)
            except Exception:
                pass

print(f"Loaded metadata for {len(episodes)} episodes")

target_guests = [
    ("brian-balfour", "Brian Balfour", "Retention, Growth Loops, PMF"),
    ("casey-winters", "Casey Winters", "Growth Loops vs Funnels, Scaling"),
    ("elena-verna", "Elena Verna", "B2B Product-Led Growth & Sales"),
    ("adam-fishman", "Adam Fishman", "Onboarding & High-Performing Growth Teams"),
    ("april-dunford", "April Dunford", "Positioning & Product-Market Fit"),
    ("madhavan-ramanujam", "Madhavan Ramanujam", "Monetization & Pricing Strategy"),
    ("shreyas-doshi", "Shreyas Doshi", "Product Management, Strategy, & Execution"),
    ("bob-moesta", "Bob Moesta", "Jobs to be Done (JTBD) & Demand"),
    ("gibson-biddle", "Gibson Biddle", "Product Strategy (DHM model)"),
    ("gustaf-alstromer", "Gustaf Alstromer", "Y Combinator, Early-Stage PMF & Growth"),
    ("hila-qu", "Hila Qu", "Product-Led Growth (PLG) & Growth Loops"),
    ("nikhyl-singhal", "Nikhyl Singhal", "Product Leadership & Career Growth"),
    ("bangaly-kaba", "Bangaly Kaba", "Adjacent User Theory & Activation"),
    ("andy-johns", "Andy Johns", "Growth Strategy & Mental Health"),
    ("erika-hall", "Erika Hall", "User Research & Customer Discovery"),
]

selected = []
for folder_prefix, guest_name, topic in target_guests:
    # Find matching episode
    matches = [e for e in episodes if folder_prefix in e["folder"] or guest_name.lower() in str(e.get("guest", "")).lower()]
    if matches:
        match = matches[0]
        match["target_topic"] = topic
        selected.append(match)
        print(f"MATCH: {match['folder']} | {match.get('guest')} | {topic}")
    else:
        print(f"NOT FOUND: {guest_name}")

print(f"\nTotal Selected: {len(selected)}")
