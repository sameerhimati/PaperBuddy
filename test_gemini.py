# test_gemini.py

from google import genai
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Initialize client
client = genai.Client(api_key=api_key)

# Test with a simple prompt
def test_gemini_api():
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",  # Use an available model
            contents="Explain what PaperBuddy does in one sentence."
        )
        print("API Response:")
        print(response.text)
        print("\nAPI Test successful!")
        
        # Try another model to verify
        print("\nTesting with another model...")
        response2 = client.models.generate_content(
            model="gemini-1.5-pro",  # Try Pro model
            contents="What does PaperBuddy do for researchers?"
        )
        print("API Response from Pro model:")
        print(response2.text)
        
        return True
    except Exception as e:
        print(f"API Test failed: {str(e)}")
        return False

# Test common Gemini models to see which ones work
def test_common_models():
    test_models = [
        "gemini-1.5-flash", 
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.0-flash", 
        "gemini-2.5-pro-preview-03-25"
    ]
    
    print("\nTesting common Gemini models:")
    working_models = []
    
    for model_name in test_models:
        try:
            print(f"Testing {model_name}...", end="")
            response = client.models.generate_content(
                model=model_name,
                contents="Hi"
            )
            print(" ✓ WORKS")
            working_models.append(model_name)
        except Exception as e:
            print(f" ✗ ERROR: {str(e)}")
    
    print("\nWorking models:")
    for model in working_models:
        print(f" - {model}")
    
    return working_models

if __name__ == "__main__":
    print("Testing Gemini API connection...")
    success = test_gemini_api()
    
    if success:
        test_common_models()