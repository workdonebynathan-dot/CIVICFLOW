import re

with open('ai_model.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Patch keyword_fallback
def kw_replacer(match):
    dept = match.group(1)
    urgency = match.group(2)
    return f'return {dept}, {urgency}, "Heuristic (Keyword)", 100.0, None'

# Use a targeted regex for the returns inside keyword_fallback
# Since all returns in keyword_fallback look like: return "Dept", urgency OR return "Dept", "Critical"
code = re.sub(r'return\s+(".*?"),\s*([^,\n]+)(?=\s*$)', kw_replacer, code, flags=re.MULTILINE)

# Wait, `analyze_permit` also has similar returns like `return "General Permission", "Medium"`.
# Let's fix analyze_permit back to what it was.
code = code.replace(
    'return "General Permission", "Medium", "Heuristic (Keyword)", 100.0, None',
    'return "General Permission", "Medium"'
)
code = code.replace(
    'return permit_reference_data[best_idx][1], permit_reference_data[best_idx][2], "Heuristic (Keyword)", 100.0, None',
    'return permit_reference_data[best_idx][1], permit_reference_data[best_idx][2]'
)

# 2. Patch analyze_complaint
# It currently returns:
# return reference_data[best_index][1], reference_data[best_index][2]
# We want to change it to return engine, confidence, alt_dept as well.
analyze_complaint_patch = """
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
"""

code = code.replace(
    'return reference_data[best_index][1], reference_data[best_index][2]',
    analyze_complaint_patch.strip()
)

# Also fix the fallback returns inside analyze_complaint:
# `return keyword_fallback(user_text)` is already returning 5 items, which is correct.

# 3. Add find_duplicate_complaint at the end
duplicate_func = """

def find_duplicate_complaint(new_text, open_complaints, threshold=0.80):
    \"\"\"
    open_complaints: list of dicts [{'tracking_id': '...', 'complaint': '...'}, ...]
    Returns tracking_id of the duplicate, or None.
    \"\"\"
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
"""

code += duplicate_func

with open('ai_model.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("ai_model.py patched successfully!")
