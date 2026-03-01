from google import genai
client = genai.Client(api_key="AIzaSyAagEfY91Z83v5nIakeyHFqR5BBr_uoSNw")
for m in client.models.list():
    print(m.name)