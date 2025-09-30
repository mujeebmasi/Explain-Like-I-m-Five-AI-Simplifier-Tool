import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

# Put your actual Gemini key here
os.environ["GEMINI_API_KEY"] = "AIzaSyBIcCMwKMUEQ272HXN1yla4QD7Iv6enaR4"

def clean_markdown_text(text: str) -> str:
    """Remove markdown formatting from text"""
    import re
    
    # Remove bold (**text** or __text__)
    text = text.replace('**', '').replace('__', '')
    
    # Remove italic (*text* or _text_)
    text = text.replace('*', '')
    
    # Remove headers (# ## ###)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Remove extra spaces and clean up
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class TextRequest(BaseModel):
    text: str
    level: str
    use_wiki: bool = True
    topic: str = ""

async def get_wikipedia_summary(topic: str):
    """Get summary from Wikipedia"""
    if not topic:
        return None
    
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
        
        async with httpx.AsyncClient() as client_http:
            response = await client_http.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "title": data.get("title"),
                    "summary": data.get("extract", "")[:200]
                }
    except Exception as e:
        print(f"Wikipedia error: {e}")
    
    return None

@app.post("/simplify")
async def simplify_text(request: TextRequest):
    try:
        # Get Wikipedia context if requested
        wiki_info = None
        if request.use_wiki and request.topic:
            wiki_info = await get_wikipedia_summary(request.topic)
        
        # Build enhanced prompt
        if wiki_info:
            prompt = f"""
Context from Wikipedia about "{wiki_info['title']}":
{wiki_info['summary']}

Now explain this for {request.level}: {request.text}

Use the Wikipedia information above to make your explanation more accurate and factual.
IMPORTANT: Write in plain text without any markdown formatting, asterisks, or special symbols.
"""
        else:
            prompt = f"Explain this for {request.level}: {request.text}. Write in plain text without any markdown formatting, asterisks, or special symbols."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        # 🎯 Clean the response text
        cleaned_text = clean_markdown_text(response.text)
        
        return {
            "simplified_text": cleaned_text,
            "used_wiki": wiki_info is not None,
            "wiki_title": wiki_info["title"] if wiki_info else None
        }
        
    except Exception as e:
        return {"simplified_text": f"Error: {str(e)}", "used_wiki": False}

@app.get("/wiki/{topic}")
async def test_wiki(topic: str):
    result = await get_wikipedia_summary(topic)
    return result or {"error": "Topic not found"}

@app.get("/")
def home():
    return {"message": "ELI5 Simplifier with Wikipedia is working!"}
