import re
import string
import nltk

# Ensure stopwords are available
try:
    from nltk.corpus import stopwords
    STOPWORDS = set(stopwords.words('english'))
except Exception:
    # Safe fallback english stopwords in case of any offline/file access issue
    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
        "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", 
        "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", 
        "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", 
        "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", 
        "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", 
        "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", 
        "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", 
        "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", 
        "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", 
        "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", 
        "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", 
        "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", 
        "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", 
        "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", 
        "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", 
        "yours", "yourself", "yourselves"
    }

URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')
HTML_PATTERN = re.compile(r'<.*?>')
WORD_PATTERN = re.compile(r'\b[a-zA-Z]{2,}\b')

def clean_text(text: str) -> str:
    """
    Cleans raw news text using Natural Language Processing techniques:
    1. Lowercase conversion
    2. Fast URL & HTML tag removal
    3. Tokenization & punctuation removal
    4. Stopword filtering with NLTK English stopwords
    5. Whitespace normalization
    Optimized for high throughput on large CSV datasets (> 600 MB).
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    text = text.strip()
    if not text:
        return ""

    # Remove URLs and HTML tags
    text = URL_PATTERN.sub('', text)
    text = HTML_PATTERN.sub('', text)

    # Fast tokenization and stopword removal in lowercase
    tokens = WORD_PATTERN.findall(text.lower())
    cleaned_tokens = [w for w in tokens if w not in STOPWORDS]

    return " ".join(cleaned_tokens)

def get_text_statistics(raw_text: str, cleaned_text: str) -> dict:
    """
    Returns basic NLP statistics for user feedback:
    original word count, cleaned word count, character count.
    """
    raw_words = len(raw_text.split()) if raw_text else 0
    cleaned_tokens = cleaned_text.split() if cleaned_text else []
    return {
        "raw_word_count": raw_words,
        "cleaned_token_count": len(cleaned_tokens),
        "raw_char_count": len(raw_text) if raw_text else 0,
        "sample_tokens": cleaned_tokens[:10]  # First 10 tokens for preview
    }
