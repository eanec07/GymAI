import urllib.request
import os
import ssl

url = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"

output_file = "data/exercises.json"

os.makedirs("data", exist_ok=True)

print("Downloading exercise database...")

context = ssl._create_unverified_context()

request = urllib.request.Request(url)

with urllib.request.urlopen(request, context=context) as response:
    data = response.read()

with open(output_file, "wb") as file:
    file.write(data)

print("Exercise database downloaded!")
print(f"Saved to: {output_file}")