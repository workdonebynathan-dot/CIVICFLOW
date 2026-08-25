import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Load data
df = pd.read_csv("data/grievances.csv")

X = df["text"]
y_dept = df["department"]
y_urg = df["urgency"]

# Vectorizer
vectorizer = TfidfVectorizer(stop_words="english")

X_vec = vectorizer.fit_transform(X)

# Models
dept_model = LogisticRegression()
urg_model = LogisticRegression()

dept_model.fit(X_vec, y_dept)
urg_model.fit(X_vec, y_urg)

# Save models
pickle.dump(vectorizer, open("model/vectorizer.pkl", "wb"))
pickle.dump(dept_model, open("model/department_model.pkl", "wb"))
pickle.dump(urg_model, open("model/urgency_model.pkl", "wb"))

print("✅ AI Model Trained Successfully")
