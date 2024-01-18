from openai import OpenAI
import base64
import requests
import time

start_time = time.time()

# Point to the local server
# client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

# using windows IP as I'm calling Python from WSL2 side
client = OpenAI(base_url="http://192.168.1.191:1234/v1", api_key="not-needed")

# roy
# client = OpenAI(base_url="http://192.168.1.218:1234/v1", api_key="not-needed")

# image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Adelie_penguins_in_the_South_Shetland_Islands.jpg/640px-Adelie_penguins_in_the_South_Shetland_Islands.jpg"

# 1.Download the image and encode it to base64
# response = requests.get(image_url)
# base64_image = base64.b64encode(response.content).decode('utf-8')

# 2.Get image locally
image_path = f'pics/hchestnut.jpg'

def encode_image(image_path):
      with open(image_path, "rb") as image_file:
          return base64.b64encode(image_file.read()).decode('utf-8')

base64_image = encode_image(image_path)

completion = client.chat.completions.create(
  model="local-model", # not used
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What’s in this image?"},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}"
          },
        },
      ],
    }
  ],
  max_tokens=1000,
  stream=True
)

for chunk in completion:
  if chunk.choices[0].delta.content:
    print(chunk.choices[0].delta.content, end="",flush=True)

end_time = time.time()
print(f"Time elapsed: {end_time - start_time} seconds")