import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity

# Add parent directory to path to import ai_model
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_model

def run_analysis():
    print("Starting Threshold Sensitivity Analysis...")
    if ai_model.model is None:
        print("AI model failed to load. Cannot run analysis.")
        return

    # Mock dataset for evaluation (Complaint Text, True Department)
    test_data = [
        ("Huge pothole on MG Road near the bakery", "PWD (Roads)"),
        ("The street light in our lane is completely broken", "KSEB"),
        ("Water pipe burst and flooded the entire street", "Water Authority"),
        ("Garbage has not been collected for a week", "Health Dept"),
        ("Someone stole my bicycle from the park", "Police"),
        ("Building is on fire please send help", "Fire Force"),
        ("Ration shop owner refusing to give rice", "Civil Supplies"),
        ("Illegal sand mining happening near the river", "Revenue Dept"),
        ("Public park walkway tiles are broken", "Municipality"),
        # Ambiguous or out-of-distribution queries
        ("I need a new passport", "Municipality"), # Should ideally fail to match confidently
        ("My neighbor's dog is barking too loud", "Police"),
        ("The internet is down in our area", "Municipality"), # Not in our DB
        ("The tree branches are touching the power lines", "KSEB"),
        ("Mosquitoes are everywhere due to stagnant water", "Health Dept")
    ]

    thresholds = np.arange(0.1, 0.95, 0.05)
    accuracies = []
    false_escalation_rates = []
    
    print(f"Evaluating {len(test_data)} test cases...")
    
    # Pre-compute embeddings for test data
    test_texts = [item[0] for item in test_data]
    test_true_labels = [item[1] for item in test_data]
    test_embeddings = ai_model.model.encode(test_texts)
    
    # Get max similarity and predicted department for each test case
    preds = []
    scores = []
    for emb in test_embeddings:
        sims = cosine_similarity([emb], ai_model.reference_embeddings)[0]
        best_idx = np.argmax(sims)
        preds.append(ai_model.reference_data[best_idx][1])
        scores.append(sims[best_idx])
        
    for thresh in thresholds:
        correct_routed = 0
        total_routed = 0
        escalated = 0
        
        for i in range(len(test_data)):
            true_label = test_true_labels[i]
            pred = preds[i]
            score = scores[i]
            
            if score >= thresh:
                # Routed by AI
                total_routed += 1
                if pred == true_label:
                    correct_routed += 1
            else:
                # Escalated to manual fallback
                escalated += 1
                
        # If nothing was routed, accuracy is 0
        accuracy = (correct_routed / total_routed * 100) if total_routed > 0 else 0
        # False escalation: cases that would have been correctly predicted by AI, but were escalated because of threshold
        # Actually, let's just plot % Escalated (Fallback Rate)
        escalation_rate = (escalated / len(test_data)) * 100
        
        accuracies.append(accuracy)
        false_escalation_rates.append(escalation_rate)

    # Find optimal threshold (e.g. maximizes accuracy while keeping escalation rate < 30%)
    optimal_idx = 0
    for i, (acc, esc) in enumerate(zip(accuracies, false_escalation_rates)):
        if acc >= 90 and esc < 40:
            optimal_idx = i
            break
            
    opt_thresh = thresholds[optimal_idx]
    
    print(f"Optimal Threshold Found: {opt_thresh:.2f}")

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(thresholds, accuracies, label='Routing Accuracy (%)', color='blue', marker='o')
    plt.plot(thresholds, false_escalation_rates, label='Escalation Rate (%)', color='red', marker='x')
    plt.axvline(x=0.35, color='gray', linestyle='--', label='Current Threshold (0.35)')
    plt.axvline(x=opt_thresh, color='green', linestyle='--', label=f'Optimal Threshold ({opt_thresh:.2f})')
    
    plt.title('Threshold Sensitivity Analysis (ROC-like Curve)')
    plt.xlabel('Confidence Threshold')
    plt.ylabel('Percentage (%)')
    plt.legend()
    plt.grid(True)
    
    plot_path = os.path.join(os.path.dirname(__file__), 'threshold_analysis.png')
    plt.savefig(plot_path)
    print(f"Analysis complete. Plot saved to {plot_path}")

if __name__ == "__main__":
    run_analysis()
