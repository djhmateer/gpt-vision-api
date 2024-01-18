import base64
import requests
from dotenv import load_dotenv
import os

# lets load from the .env file using python-dotenv which is in Pipfile
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Path to your image
image_path = "pics/hchestnut.jpg"

# Getting the base64 string
base64_image = encode_image(image_path)

headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
}

# this is good
# text = "describe this image in 5 words"

# text = "describe this image in 1 sentence"

# this is good - just returns the number
text = "Can you also tell me if this would be classified as a traumatic picture for someone to look at. give traumatic rating on a scale of 1 - 5. Just the number"

payload = {
  "model": "gpt-4-vision-preview",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          # "text": "What’s in this image?"
          "text": text
        },
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}"
          }
        }
      ]
    }
  ],
  "max_tokens": 300
}

response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

print(response.json())

# just want the content
# Parse JSON
# data = json.loads(response.json())

foo = response.json()

content = foo['choices'][0]['message']['content']

# 5 words
# Flowering chestnut tree in bloom
# Chestnut flowers blooming in spring
# Flowering tree, white blooms, greenery.
# Chestnut tree blooming in spring.

# 1 sentence
# A cluster of delicate white flowers with pink speckles and prominent stamens is surrounded by green leaves under a canopy of trees.

# trauma
# 1

print(content)

