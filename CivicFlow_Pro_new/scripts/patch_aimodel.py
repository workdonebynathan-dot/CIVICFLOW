import re

with open('ai_model.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Patch keyword_fallback returns
content = re.sub(
    r'return "([^"]+)", ("[^"]+"|urgency(?: if urgency == "Critical" else "High")?)',
    r'return "\1", \2, "Heuristic (Keyword)", 100.0, None',
    content
)
# Ensure we only patch in keyword_fallback. The regex might have hit something else? No, only keyword_fallback has those returns. Wait, analyze_permit is there but it returns 'General Permission', 'Medium'. Let's fix analyze_permit to normal.
# Oh, analyze_permit returns: return "General Permission", "Medium" -> return "General Permission", "Medium", "Heuristic (Keyword)", 100.0, None
# I should undo that for analyze_permit or just be specific.

# Let's do a more robust string replacement for ai_model.py
import sys
sys.exit(0)
