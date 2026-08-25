import sys
import os
import time
import matplotlib.pyplot as plt
from deep_translator import GoogleTranslator

# Add parent directory to path to import ai_model
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_model

def run_evaluation():
    print("Starting Multilingual Routing Evaluation (Malayalam vs English)...")
    if ai_model.model is None:
        print("AI model failed to load. Cannot run analysis.")
        return

    # Dataset: English and corresponding Malayalam translations, plus the expected Department
    dataset = [
        ("Huge pothole on MG Road", "എംജി റോഡിൽ വലിയ കുഴി", "PWD (Roads)"),
        ("Water pipe burst and flooded the street", "വെള്ള പൈപ്പ് പൊട്ടി റോഡിൽ വെള്ളം കയറി", "Water Authority"),
        ("Street light is broken", "തെരുവ് വിളക്ക് കേടാണ്", "KSEB"),
        ("Garbage has not been collected", "മാലിന്യം ശേഖരിച്ചിട്ടില്ല", "Health Dept"),
        ("Building is on fire", "കെട്ടിടത്തിന് തീപിടിച്ചു", "Fire Force"),
        ("Someone stole my bike", "ആരോ എന്റെ ബൈക്ക് മോഷ്ടിച്ചു", "Police"),
        ("Illegal sand mining in the river", "നദിയിൽ അനധികൃത മണലെടുപ്പ്", "Revenue Dept"),
        ("Ration shop is closed", "റേഷൻ കട അടച്ചിട്ടിരിക്കുന്നു", "Civil Supplies"),
        ("Drainage is blocked", "ഡ്രെയിനേജ് ബ്ലോക്കായി", "Municipality"),
        ("Live electric wire has fallen", "വൈദ്യുതി കമ്പി പൊട്ടിവീണു", "KSEB")
    ]

    eng_correct = 0
    mal_correct = 0
    eng_latencies = []
    mal_latencies = []
    
    translator = GoogleTranslator(source='auto', target='en')

    print(f"Evaluating {len(dataset)} samples...")

    for eng_text, mal_text, true_dept in dataset:
        # Evaluate English
        t0 = time.time()
        eng_pred, _, _, _, _ = ai_model.analyze_complaint(eng_text)
        t1 = time.time()
        eng_latencies.append((t1 - t0) * 1000) # ms
        if eng_pred == true_dept:
            eng_correct += 1

        # Evaluate Malayalam (Requires translation overhead)
        t2 = time.time()
        try:
            translated_text = translator.translate(mal_text)
        except:
            translated_text = mal_text
        mal_pred, _, _, _, _ = ai_model.analyze_complaint(translated_text)
        t3 = time.time()
        mal_latencies.append((t3 - t2) * 1000) # ms
        if mal_pred == true_dept:
            mal_correct += 1

    eng_accuracy = (eng_correct / len(dataset)) * 100
    mal_accuracy = (mal_correct / len(dataset)) * 100
    avg_eng_latency = sum(eng_latencies) / len(eng_latencies)
    avg_mal_latency = sum(mal_latencies) / len(mal_latencies)

    print(f"English Accuracy: {eng_accuracy:.1f}%")
    print(f"Malayalam Accuracy: {mal_accuracy:.1f}%")
    print(f"Avg English Latency (ms): {avg_eng_latency:.1f}")
    print(f"Avg Malayalam Latency (ms): {avg_mal_latency:.1f}")
    print(f"Translation Overhead (ms): {avg_mal_latency - avg_eng_latency:.1f}")

    # Plotting
    labels = ['English', 'Malayalam (Translated)']
    accuracies = [eng_accuracy, mal_accuracy]
    latencies = [avg_eng_latency, avg_mal_latency]

    fig, ax1 = plt.subplots(figsize=(8, 5))

    color = 'tab:blue'
    ax1.set_ylabel('Accuracy (%)', color=color)
    bars = ax1.bar(labels, accuracies, color=color, width=0.4)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(0, 100)

    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('Latency (ms)', color=color)  
    line = ax2.plot(labels, latencies, color=color, marker='o', linestyle='-', linewidth=2, markersize=8)
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Add values on bars
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.1f}%', va='bottom', ha='center', color='black', fontweight='bold')

    plt.title('Routing Accuracy and Latency Overhead (English vs Malayalam)')
    fig.tight_layout()  
    plot_path = os.path.join(os.path.dirname(__file__), 'multilingual_eval.png')
    plt.savefig(plot_path)
    print(f"Analysis complete. Plot saved to {plot_path}")

if __name__ == "__main__":
    run_evaluation()
