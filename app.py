from google import genai

client = genai.Client(api_key="AIzaSyBe5J5yMNK7L0U2Mie3D-yD3xrdd-WiYpg")

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents="Onde encontro restaurantes em União da Vitória?"
)
print(response.text)