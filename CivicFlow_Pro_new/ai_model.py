import numpy as np
import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# --- GLOBAL INITIALIZATION (Prevents NameErrors if loading fails) ---
model = None
reference_embeddings = None
permit_embeddings = None

# ==========================================
# 1. THE SAFETY NET (Advanced Keyword Fallback)
# ==========================================
# This runs if the AI fails, is unsure (< 35%), or is offline.
def keyword_fallback(text):
    text = text.lower()
    
    # --- Urgency Detection ---
    urgency = "High" # Default
    critical_keywords = ['fire', 'spark', 'collapse', 'gas', 'explosion', 'blood', 'accident', 'death', 'danger', 'live wire', 'burning', 'poison', 'trapped']
    medium_keywords = ['street light', 'park', 'dog', 'waste', 'garbage', 'smell', 'mosquito', 'cleaning', 'ration', 'shop']
    
    if any(w in text for w in critical_keywords): urgency = "Critical"
    elif any(w in text for w in medium_keywords): urgency = "Medium"

    # --- Department Routing (9 Depts) ---

    # 🔥 Fire Force (Emergency)
    if any(w in text for w in ['fire', 'flame', 'smoke', 'gas', 'burn', 'cylinder', 'explosion', 'trapped']):
        return "Fire Force", "Critical", "Heuristic (Keyword)", 100.0, None

    # 🚓 Police (Law & Order)
    if any(w in text for w in ['theft', 'robbery', 'fight', 'crime', 'stolen', 'drunk', 'weapon', 'snatch', 'traffic', 'nuisance', 'police', 'harassment']):
        return "Police", urgency if urgency == "Critical" else "High", "Heuristic (Keyword)", 100.0, None

    # ⚡ KSEB (Electricity)
    if any(w in text for w in ['current', 'power', 'light', 'pole', 'shock', 'voltage', 'wire', 'transformer', 'fuse', 'meter', 'spark', 'blackout', 'bill']):
        return "KSEB", urgency, "Heuristic (Keyword)", 100.0, None

    # 🛣️ PWD (Roads)
    if any(w in text for w in ['road', 'pothole', 'tar', 'bridge', 'gutter', 'highway', 'street', 'surface', 'tarmac', 'divider', 'flyover', 'sinkhole', 'speed breaker']):
        return "PWD (Roads)", urgency, "Heuristic (Keyword)", 100.0, None

    # 💧 Water Authority
    if any(w in text for w in ['water', 'pipe', 'leak', 'drainage', 'sewage', 'supply', 'burst', 'valve', 'pressure', 'fountain', 'drinking']):
        return "Water Authority", urgency, "Heuristic (Keyword)", 100.0, None

    # 🚑 Health Dept
    if any(w in text for w in ['waste', 'garbage', 'smell', 'mosquito', 'food', 'clean', 'rotten', 'poison', 'hospital', 'plastic', 'dengue']):
        return "Health Dept", "High", "Heuristic (Keyword)", 100.0, None

    # 🌾 Civil Supplies
    if any(w in text for w in ['ration', 'rice', 'wheat', 'kerosene', 'food supply', 'shop closed', 'sugar', 'card']):
        return "Civil Supplies", "Medium", "Heuristic (Keyword)", 100.0, None

    # 📜 Revenue Dept
    if any(w in text for w in ['land', 'encroach', 'wetland', 'paddy', 'survey', 'filling', 'illegal building']):
        return "Revenue Dept", "Medium", "Heuristic (Keyword)", 100.0, None

    # 🏛️ Municipality (Civil Works & General) - The "Catch-All"
    if any(w in text for w in ['pathway', 'park', 'walkway', 'public', 'garden', 'slab', 'footpath', 'maintenance', 'dog', 'animal', 'toilet', 'drain', 'manhole', 'slaughter']):
        return "Municipality", "Medium", "Heuristic (Keyword)", 100.0, None
    
    # Absolute Default
    return "Municipality", "Medium", "Heuristic (Keyword)", 100.0, None

# ==========================================
# 2. LOAD THE ADVANCED AI MODEL
# ==========================================
print("Loading Advanced AI Model (MPNet)... This allows for high-accuracy understanding.")

try:
    # Using 'all-mpnet-base-v2' (High Accuracy Microsoft Model)
    model = SentenceTransformer('all-mpnet-base-v2')
    print("✅ MPNet AI Model Loaded & Ready!")
except Exception as e:
    print(f"⚠️ Warning: Model failed to download. Check internet. Error: {e}")

# ==========================================
# 3. MASSIVE KNOWLEDGE BASE (The Textbook)
# ==========================================
reference_data = [
    # 🛣️ PWD (ROADS & BRIDGES)
    ("There is a massive pothole in the middle of the road", "PWD (Roads)", "High"),
    ("The road surface is completely broken and full of craters", "PWD (Roads)", "High"),
    ("A bridge pillar looks cracked and dangerous", "PWD (Roads)", "Critical"),
    ("The bridge creates a loud shaking noise when cars pass", "PWD (Roads)", "Critical"),
    ("Landslide has blocked the mountain highway", "PWD (Roads)", "Critical"),
    ("Huge sinkhole appeared on the tarmac", "PWD (Roads)", "Critical"),
    ("Road divider is broken and causing accidents", "PWD (Roads)", "High"),
    ("Speed breaker is too high and unmarked", "PWD (Roads)", "Medium"),
    ("Traffic signboard is broken or fallen down", "PWD (Roads)", "Medium"),
    ("Tar has melted and the road is slippery", "PWD (Roads)", "High"),
    ("Retaining wall on the roadside has collapsed", "PWD (Roads)", "High"),

    # 🏛️ MUNICIPALITY (CIVIL WORKS, DRAINS & PATHWAYS)
    ("The public area nearby is not properly maintained", "Municipality", "Medium"),
    ("Pathways are damaged and walking is difficult", "Municipality", "Medium"),
    ("Public park walking track is broken", "Municipality", "Medium"),
    ("Footpath slabs are missing and dangerous for pedestrians", "Municipality", "Medium"),
    ("The walkway tiles are broken and loose", "Municipality", "Medium"),
    ("Drainage is blocked and overflowing onto the road", "Municipality", "High"),
    ("Sewage water is entering houses due to block", "Municipality", "Critical"),
    ("Manhole cover is missing and someone might fall in", "Municipality", "Critical"),
    ("Stray dog menace is increasing in the street", "Municipality", "Medium"),
    ("Dead animal lying on the road needs removal", "Municipality", "High"),
    ("Building construction is illegal and encroaching road", "Municipality", "High"),
    ("Public toilet is unclean and unusable", "Municipality", "Medium"),
    ("Street sweeping has not been done for weeks", "Municipality", "Medium"),

    # ⚡ KSEB (ELECTRICITY)
    ("Live electric wire has fallen on the street and is sparking", "KSEB", "Critical"),
    ("Transformer is smoking and looks like it will explode", "KSEB", "Critical"),
    ("Electric pole is leaning dangerously over a house", "KSEB", "Critical"),
    ("Tree branch fell on the power lines causing sparks", "KSEB", "Critical"),
    ("No electricity supply in our entire neighborhood for 4 hours", "KSEB", "High"),
    ("Voltage is fluctuating and damaging our appliances", "KSEB", "High"),
    ("Street light is not working and it is pitch dark", "KSEB", "Medium"),
    ("Street light is flickering constantly", "KSEB", "Medium"),
    ("Electric meter is faulty and showing wrong reading", "KSEB", "Medium"),
    ("Underground cable seems to be exposed", "KSEB", "High"),

    # 💧 Water Authority (PIPELINES)
    ("Main water pipeline has burst and road is flooded", "Water Authority", "High"),
    ("Huge fountain of water leaking from the street pipe", "Water Authority", "High"),
    ("No water supply in our colony for the last 2 days", "Water Authority", "High"),
    ("Drinking water smells like sewage and is dirty", "Water Authority", "Critical"),
    ("Water pressure is extremely low in our area", "Water Authority", "Medium"),
    ("Water meter is leaking", "Water Authority", "Medium"),
    ("Valve is stuck and water won't stop flowing", "Water Authority", "High"),
    ("Pipe connection is broken near the meter", "Water Authority", "Medium"),

    # 🚑 HEALTH DEPARTMENT (WASTE & HYGIENE)
    ("Garbage pile is accumulating and rotting nearby", "Health Dept", "High"),
    ("Terrible foul smell coming from the waste dump", "Health Dept", "High"),
    ("Neighbor is burning plastic and causing toxic smoke", "Health Dept", "High"),
    ("Mosquito breeding is high due to stagnant water", "Health Dept", "Medium"),
    ("Hotel food caused food poisoning to many people", "Health Dept", "Critical"),
    ("Septic tank waste is being dumped in the river", "Health Dept", "Critical"),
    ("Hospital waste is dumped on the roadside", "Health Dept", "Critical"),
    ("Dead rats are causing smell and disease risk", "Health Dept", "High"),

    # 🚓 POLICE (LAW & ORDER)
    ("Robbery in progress at a shop", "Police", "Critical"),
    ("Thieves broke into a house nearby", "Police", "Critical"),
    ("Suspicious group fighting with weapons", "Police", "Critical"),
    ("Drunk people creating nuisance on the street", "Police", "High"),
    ("Loud noise from speakers disturbing sleep at night", "Police", "Medium"),
    ("Traffic jam is stuck for hours due to bad parking", "Police", "Medium"),
    ("Chain snatching incident happened just now", "Police", "Critical"),
    ("Drug selling activity suspected in the park", "Police", "High"),
    ("Vehicle is parked wrongly blocking the gate", "Police", "Medium"),
    ("Women are being harassed at the bus stop", "Police", "Critical"),

    # 🔥 FIRE FORCE
    ("A building is on fire", "Fire Force", "Critical"),
    ("Gas leak smell coming from a house or shop", "Fire Force", "Critical"),
    ("Vehicle caught fire on the road", "Fire Force", "Critical"),
    ("Huge fire in the garbage dump yard", "Fire Force", "Critical"),
    ("Animal trapped in a high well or tree", "Fire Force", "Medium"),

    # 🌾 REVENUE & CIVIL SUPPLIES
    ("Ration shop is closed during working hours", "Civil Supplies", "Medium"),
    ("Ration rice quality is full of stones and worms", "Civil Supplies", "High"),
    ("Shopkeeper is refusing to give ration goods", "Civil Supplies", "High"),
    ("Someone is filling a wetland or paddy field illegally", "Revenue Dept", "High"),
    ("Government land is being encroached by private party", "Revenue Dept", "High"),
    ("River sand mining is happening illegally", "Revenue Dept", "Critical"),
]

# --- PERMISSIONS DATA ---
permit_reference_data = [
    ("I am building a new house and need plan approval", "Building Plan Approval", "High"),
    ("Need to start the foundation work for my building", "Commencement Certificate", "Medium"),
    ("Building is finished, need certificate to move in", "Occupancy Certificate", "Medium"),
    ("I want to dig a borewell for water in my property", "Borewell Permission", "High"),
    ("Renovating a shop near an old monument or airport", "Heritage/Airport NOC", "Medium"),
    ("Need to dig the road to lay a water pipe or cable", "Road Cutting Permission", "High"),
    ("A tree in my private land is dangerous and needs cutting", "Tree Felling Permit", "Medium"),
    ("Installing a large generator or lift in the apartment", "Electrical Inspectorate Approval", "High"),
    ("Using a loudspeaker for a wedding or public rally", "Loudspeaker Permission", "Medium"),
    ("Conducting a protest or wedding march on the main road", "Procession/Assembly Permission", "High"),
    ("Playing music at a public concert or event", "Performance License", "Medium"),
    ("Selling tickets for a public show or entertainment", "Entertainment Tax Clearance", "Medium"),
    ("Transferring car ownership or moving to another state", "RTO NOC", "Medium"),
    ("Applying for a passport as a government employee", "Passport NOC", "Medium"),
    ("Need pollution clearance for a new restaurant or hall", "Marriage Hall/Restaurant NOC", "High"),
    ("Starting a new shop or business activity in the city", "Trade License", "Medium"),
    ("Selling food items or starting a catering business", "FSSAI Permit", "High"),
    ("Disposing of chemical waste or medical batteries", "Hazardous Waste Authorization", "Critical")
]

# Pre-calculate all embeddings for speed
if model is not None:
    try:
        ref_texts = [item[0] for item in reference_data]
        reference_embeddings = model.encode(ref_texts)

        prm_texts = [p[0] for p in permit_reference_data]
        permit_embeddings = model.encode(prm_texts)
        print("✅ All Semantic Embeddings Pre-calculated")
    except Exception as e:
        print(f"⚠️ AI Vectorization Error: {e}")

# ==========================================
# 4. THE ANALYSIS FUNCTIONS
# ==========================================

def analyze_complaint(user_text):
    """Categorizes public grievances into departments"""
    # Safety Check: If model or embeddings failed, use fallback
    if model is None or reference_embeddings is None:
        return keyword_fallback(user_text)
        
    try:
        user_embedding = model.encode([user_text])
        similarities = cosine_similarity(user_embedding, reference_embeddings)[0]
        best_index = np.argmax(similarities)
        
        if similarities[best_index] < 0.35:
            return keyword_fallback(user_text)

        dept = reference_data[best_index][1]
        urg = reference_data[best_index][2]
        confidence = float(similarities[best_index] * 100)
        
        # Find alt_dept (second highest)
        alt_dept = None
        if len(similarities) > 1:
            sorted_indices = np.argsort(similarities)[::-1]
            for idx in sorted_indices[1:]:
                if reference_data[idx][1] != dept:
                    alt_dept = reference_data[idx][1]
                    break
                    
        return dept, urg, "Semantic (MPNet)", confidence, alt_dept
    except Exception as e:
        print(f"❌ AI Error in analyze_complaint: {e}")
        return keyword_fallback(user_text)

def analyze_permit(motive_text):
    """Categorizes the motive for the permission portal"""
    # Safety Check: If model or embeddings failed, use fallback
    if model is None or permit_embeddings is None:
        return "General Permission", "Medium"

    try:
        motive_embedding = model.encode([motive_text])
        similarities = cosine_similarity(motive_embedding, permit_embeddings)[0]
        best_idx = np.argmax(similarities)
        score = similarities[best_idx]
        
        # Threshold check
        if score < 0.35:
            return "General Permission", "Medium"
            
        return permit_reference_data[best_idx][1], permit_reference_data[best_idx][2]
    except Exception as e:
        print(f"❌ AI Error in analyze_permit: {e}")
        return "General Permission", "Medium"

def find_duplicate_complaint(new_text, open_complaints, threshold=0.80):
    """
    open_complaints: list of dicts [{'tracking_id': '...', 'complaint': '...'}, ...]
    Returns tracking_id of the duplicate, or None.
    """
    if not open_complaints or model is None:
        return None
        
    try:
        new_embedding = model.encode([new_text])
        open_texts = [c['complaint'] for c in open_complaints]
        open_embeddings = model.encode(open_texts)
        
        similarities = cosine_similarity(new_embedding, open_embeddings)[0]
        best_idx = np.argmax(similarities)
        
        if similarities[best_idx] > threshold:
            return open_complaints[best_idx]['tracking_id']
    except Exception as e:
        print(f"❌ Error in find_duplicate_complaint: {e}")
        
    return None
