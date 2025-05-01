import torch

def get_device():
    """
    Returns 'cuda' if GPU is available and config allows, else 'cpu'.
    """
    if torch.cuda.is_available():
        print("🚀 Using GPU for inference!")
        return 'cuda'
    else:
        print("⚡ Using CPU for inference.")
        return 'cpu'

def safe_request(url, timeout=10):
    """
    Makes a safe HTTP request. Returns None if fails.
    """
    import requests
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None