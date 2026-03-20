import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Import the Google ADK classes
from google.adk.agents import Agent
from google.adk.tools import Tool

load_dotenv()

# ==========================================
# 1. Complex State & Mock Databases Let's simulate Regional Need Context!
# ==========================================
CHARITIES = {
    "c1": {"name": "Downtown Soup Kitchen", "needs": ["vegetables", "fruit", "bread"], "distance_miles": 2.5, "fridge": True, "zip_code": "90210"},
    "c2": {"name": "Westside Family Pantry", "needs": ["canned goods", "meat", "dairy"], "distance_miles": 5.0, "fridge": True, "zip_code": "90211"},
    "c3": {"name": "Community Food Bank", "needs": ["any"], "distance_miles": 12.0, "fridge": False, "zip_code": "90212"}
}

REGIONAL_ECONOMIC_DATA = {
    "90210": {"food_insecurity_index": "High", "recent_events": "Local factory closed, high demand for immediate hot meals."},
    "90211": {"food_insecurity_index": "Medium", "recent_events": "Stable demand."},
    "90212": {"food_insecurity_index": "Low", "recent_events": "Well funded this quarter."}
}

# Ensure an output directory exists for our generated documents
OUTPUT_DIR = "harvestlink_logistics_docs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# 2. Define Advanced Logistics Actions (Tools)
# ==========================================

def get_regional_need(zip_code: str) -> str:
    """Fetches real-time regional economic data and food insecurity index for a zip code."""
    print(f"  📈 [SYSTEM] Fetching regional economic data for Zip {zip_code}...")
    data = REGIONAL_ECONOMIC_DATA.get(zip_code, {"food_insecurity_index": "Unknown", "recent_events": "No data."})
    return json.dumps(data)

def find_best_charity(category: str, max_spoilage_hours: int) -> str:
    """Finds the ID and Zip Code of the best charities based on food category and spoilage time. Returns a JSON list of matches."""
    print(f"  🤖 [SYSTEM] Finding valid charities for {category} (Spoils in {max_spoilage_hours}h)...")
    
    valid_matches = []
    for c_id, data in CHARITIES.items():
        needs = data["needs"]
        if "any" in needs or category.lower() in needs:
            # Spoilage Logic
            if max_spoilage_hours < 12 and not data["fridge"]:
                continue 
            valid_matches.append({
                "charity_id": c_id, 
                "name": data["name"], 
                "zip_code": data["zip_code"],
                "distance": data["distance_miles"]
            })
            
    if valid_matches:
        return json.dumps(valid_matches)
    return "No suitable charity found."

def dispatch_fleet_driver(charity_id: str, food_items: list) -> str:
    """Dispatches a fleet driver (e.g. DoorDash/Volunteer network). Pass the charity ID and list of food items as JSON."""
    if charity_id not in CHARITIES:
        return "Failed: Invalid Charity ID"
        
    charity_name = CHARITIES[charity_id]['name']
    item_summary = ", ".join([f"{item['amount']}lbs {item['name']}" for item in food_items])
    print(f"  🚀 [PHYSICAL ACTION] Dispatched Gig-Driver to deliver {item_summary} to {charity_name}.")
    
    # Simulate routing delay
    time.sleep(1)
    return f"Success: Driver routed to {charity_name}. ETA 14 mins."

def generate_financial_docs(donor_name: str, charity_id: str, food_items: list, estimated_value_usd: float) -> str:
    """Generates the official Tax-Deductible Receipt for the donor, and the Bill of Lading for the charity."""
    charity_name = CHARITIES[charity_id]['name']
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    item_str = "\n".join([f" - {item['amount']}lbs {item['name']}" for item in food_items])
    
    # 1. Create Tax Receipt
    receipt = f"""=================================
TAX DEDUCTIBLE RECEIPT
HarvestLink Logistics Network
=================================
Date: {timestamp}
Donor: {donor_name}
Total Estimated Value: ${estimated_value_usd:.2f}

Thank you for reducing food waste and feeding your community!
================================="""
    
    with open(f"{OUTPUT_DIR}/tax_receipt_{donor_name.replace(' ','_')}.txt", "w") as f:
        f.write(receipt)
    print(f"  🧾 [DIGITAL ACTION] Generated Tax Receipt: {OUTPUT_DIR}/tax_receipt_{donor_name.replace(' ','_')}.txt")

    # 2. Create Bill of Lading
    bol = f"""=================================
BILL OF LADING (INBOUND)
Destination: {charity_name}
=================================
Date: {timestamp}
Donor Origin: {donor_name}

INCOMING INVENTORY:
{item_str}

Please ensure team is ready for receipt.
================================="""
    
    with open(f"{OUTPUT_DIR}/bill_of_lading_{charity_id}.txt", "w") as f:
        f.write(bol)
    print(f"  📋 [DIGITAL ACTION] Generated Bill Of Lading: {OUTPUT_DIR}/bill_of_lading_{charity_id}.txt")

    return "Success: Financial and Logistics documents generated and emailed."

# ==========================================
# 3. Assemble the Toolkit
# ==========================================
tools = [
    Tool(
        name="find_best_charity",
        description="Finds valid charities for a food category. Returns a JSON list of matches including distance and zip_code. You should prioritize charities with highest need.",
        func=find_best_charity
    ),
    Tool(
        name="get_regional_need",
        description="Checks the economic data and 'food insecurity index' for a given zip code. Use this to break ties between charities.",
        func=get_regional_need
    ),
    Tool(
        name="dispatch_fleet_driver",
        description="Dispatches the actual vehicle. Requires charity_id and a list of food_items [{'name': str, 'amount': int}].",
        func=dispatch_fleet_driver
    ),
    Tool(
        name="generate_financial_docs",
        description="Generates Tax Receipts and Bills of Lading. Requires donor_name, charity_id, food_items list, and estimated total USD value.",
        func=generate_financial_docs
    )
]

# ==========================================
# 4. Create the Autonomous ADK Agent
# ==========================================
harvest_agent = Agent(
    name="HarvestLink Omni-Router",
    instructions=(
        "You are the autonomous 'Brain' of HarvestLink. You receive messy real-world inputs (texts, simulated images of pallets, voice transcripts) from grocery stores."
        "Your goal is to completely automate the supply chain of this surplus food.\n"
        "STEPS YOU MUST FOLLOW:\n"
        "1. Extract the food items, volume, and spoil time from the user's messy input.\n"
        "2. Call `find_best_charity` to see who can accept this food.\n"
        "3. Wait! Don't just pick the closest one. Iterate through the matches and call `get_regional_need` on their zip codes to find out who has the highest 'food_insecurity_index' right now.\n"
        "4. Pick the charity that has the highest need (or is safest from spoilage).\n"
        "5. Call `dispatch_fleet_driver` to route the gig-worker to the chosen charity.\n"
        "6. Call `generate_financial_docs` to instantly create the IRS compliance receipt and the charity's inventory Bill of Lading.\n"
        "7. Finally, explain to the human reading your log exactly why you chose that charity (mentioning the economic data) and summarize the logistics actions."
    ),
    tools=tools,
    model="gemini-2.5-flash"
)

# ==========================================
# 5. Run the Simulation
# ==========================================
if __name__ == "__main__":
    # If running in Google Cloud Run, it provides a 'PORT' environment variable
    port = os.environ.get("PORT")
    
    if port:
        print(f"Starting built-in ADK API Server on port {port}...")
        # Utilize the google-adk native FastAPI/Swagger server
        try:
            from google.adk.server import serve
            serve(harvest_agent, host="0.0.0.0", port=int(port))
        except ImportError:
            # Fallback if the serve method is directly on the agent in this ADK version
            harvest_agent.serve(host="0.0.0.0", port=int(port))
    else:
        # Standard local CLI mock simulation you can run in your terminal
        messy_multimodal_input = (
            "VOICE MEMO FROM MANAGER: 'Hey HarvestLink, it's John at Safeway. I've got a pallet of fresh produce that didn't sell."
            "About 60 pounds of vegetables total. They look fine now but will definitely spoil in under 24 hours if not used.'\n\n"
            "ATTACHED UNSTRUCTURED EMAIL: 'Please value this pallet at $120 for our corporate tax write-off. - Safeway Mgmt'"
        )
                          
        print("--------------------------------------------------")
        print("🎙️ INGESTING MESSY DATA (Voice + Emails)...")
        print(f"{messy_multimodal_input}")
        print("--------------------------------------------------\n")
        
        print("🧠 ADK AGENT: Processing multimodal intent, checking regional metrics, and routing...\n")
        
        response = harvest_agent.run(messy_multimodal_input)
        
        print("\n==================================================")
        print("🏁 FINAL HARVESTLINK ACTION REPORT")
        print("==================================================")
        print(response)
        print("==================================================")
