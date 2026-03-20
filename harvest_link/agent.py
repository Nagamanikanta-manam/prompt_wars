import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

from google.adk.agents import Agent

load_dotenv()

# ==========================================
# Mock Data
# ==========================================
CHARITIES = {
    "c1": {"name": "Downtown Soup Kitchen", "needs": ["vegetables", "fruit", "bread"], "distance_miles": 2.5, "fridge": True, "zip_code": "90210"},
    "c2": {"name": "Westside Family Pantry", "needs": ["canned goods", "meat", "dairy"], "distance_miles": 5.0, "fridge": True, "zip_code": "90211"},
    "c3": {"name": "Community Food Bank", "needs": ["any"], "distance_miles": 12.0, "fridge": False, "zip_code": "90212"}
}

REGIONAL_ECONOMIC_DATA = {
    "90210": {"food_insecurity_index": "High", "recent_events": "High demand due to factory closure"},
    "90211": {"food_insecurity_index": "Medium", "recent_events": "Stable demand"},
    "90212": {"food_insecurity_index": "Low", "recent_events": "Well funded"}
}

OUTPUT_DIR = "harvestlink_docs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# Tools
# ==========================================

def get_regional_need(zip_code: str) -> str:
    data = REGIONAL_ECONOMIC_DATA.get(zip_code, {"food_insecurity_index": "Unknown"})
    return json.dumps(data)


def find_best_charity(category: str, max_spoilage_hours: int) -> str:
    matches = []

    for cid, data in CHARITIES.items():
        if "any" in data["needs"] or category.lower() in data["needs"]:
            if max_spoilage_hours < 12 and not data["fridge"]:
                continue

            matches.append({
                "charity_id": cid,
                "name": data["name"],
                "zip_code": data["zip_code"],
                "distance": data["distance_miles"]
            })

    return json.dumps(matches) if matches else "No charity"


def dispatch_fleet_driver(charity_id: str, food_items: str) -> str:
    items = json.loads(food_items)

    charity = CHARITIES[charity_id]["name"]
    summary = ", ".join([f"{i['amount']}lbs {i['name']}" for i in items])

    print(f"[ACTION] Dispatch → {charity} with {summary}")
    time.sleep(1)

    return f"Driver sent to {charity}"


def generate_financial_docs(
    donor_name: str,
    charity_id: str,
    food_items: str,
    estimated_value_usd: float
) -> str:
    items = json.loads(food_items)

    charity = CHARITIES[charity_id]["name"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    item_str = "\n".join([f"{i['amount']}lbs {i['name']}" for i in items])

    # Receipt
    with open(f"{OUTPUT_DIR}/receipt.txt", "w") as f:
        f.write(f"Donor: {donor_name}\nValue: ${estimated_value_usd}\nDate: {timestamp}")

    # Bill of Lading
    with open(f"{OUTPUT_DIR}/bol.txt", "w") as f:
        f.write(f"Destination: {charity}\nItems:\n{item_str}")

    print("[ACTION] Documents generated")

    return "Docs created"


# ==========================================
# Agent
# ==========================================
tools = [
    find_best_charity,
    get_regional_need,
    dispatch_fleet_driver,
    generate_financial_docs
]

root_agent = Agent(
    name="HarvestLink",
    instruction=(
        "Extract food info from messy input. "
        "Use tools step by step.\n"
        "IMPORTANT: When passing food_items, use JSON string like "
        "[{\"name\": \"vegetables\", \"amount\": 60}]"
    ),
    tools=tools,
    model="gemini-2.5-flash"
)

# ==========================================
# Run
# ==========================================
if __name__ == "__main__":
    port = os.environ.get("PORT")

    if port:
        from google.adk.server import serve
        serve(root_agent, host="0.0.0.0", port=int(port))
    else:
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        from google.genai import types

        runner = Runner(
            app_name="harvest_link",
            agent=root_agent,
            session_service=InMemorySessionService(),
            auto_create_session=True
        )

        message = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="We have 60 pounds of vegetables expiring in 24 hours"
            )]
        )

        for event in runner.run(
            user_id="u1",
            session_id="s1",
            new_message=message
        ):
            if event.content:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)