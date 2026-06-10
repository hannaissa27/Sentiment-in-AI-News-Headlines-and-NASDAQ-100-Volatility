import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .utils import force_float

class SentimentEngine:
    def __init__(self, model_name):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
    
    def _load_model(self):
        """Lazy loading: only load the heavy model when we actually need it."""
        if self.model is None:
            print(f"Loading AI Model ({self.model_name})...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                self.model.eval()
            except Exception as e:
                print(f"Error loading model: {e}")

    def get_score(self, text):
        """Returns score: Positive - Negative (Range: -1.0 to 1.0)"""
        if not text: return 0.0
        
        self._load_model()
        if self.model is None: return 0.0

        try:
            inputs = self.tokenizer(str(text), return_tensors="pt", padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=1)
            
            # FinBERT Output: Index 0=Positive, Index 1=Negative
            pos = probs[0][0].item()
            neg = probs[0][1].item()
            
            return force_float(pos - neg)
        except:
            return 0.0