import pandas as pd
from pathlib import Path

faqs_path = Path(__file__).parent / "resources/faq_data.csv"

def ingest_faq_data(path):
    df = pd.read_csv(path)

if __name__ == "__main__":
    print(faqs_path)